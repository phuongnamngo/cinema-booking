import json
import urllib.error
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.bookings import services as booking_services
from apps.bookings.models import Booking
from apps.bookings.tests import seat
from apps.users.models import User

from .gateways import sign_querydr, sign_vnpay, verify_vnpay, VNPayGateway
from .models import Payment
from .tests import TEST_SETTINGS, PaymentFlowMixin
from . import services

GOLDEN_SECRET = "test-vnpay-secret"
GOLDEN_PARAMS = {
    "vnp_Version": "2.1.0",
    "vnp_Command": "pay",
    "vnp_TmnCode": "TESTTMN",
    "vnp_Amount": "15000000",
    "vnp_CurrCode": "VND",
    "vnp_TxnRef": "a" * 32,
    "vnp_OrderInfo": "Booking",
    "vnp_OrderType": "other",
    "vnp_Locale": "vn",
    "vnp_ReturnUrl": "http://localhost:5173/bookings/ABC",
    "vnp_IpAddr": "127.0.0.1",
    "vnp_CreateDate": "20261002120000",
}
GOLDEN_HASH = (
    "2c01950cf0c6b9e522f28029290928b13d7d7e865d553a0a55bae39643def704"
    "b490910d36f68c91d4eae9c3c79ec81ce2f6b9436545a1ed6f418689d05820c0"
)


class VNPaySignTests(SimpleTestCase):
    def test_sign_vnpay_matches_golden_vector_and_rejects_tampering(self):
        digest = sign_vnpay(GOLDEN_PARAMS, GOLDEN_SECRET)
        self.assertEqual(digest, GOLDEN_HASH)
        self.assertTrue(verify_vnpay({**GOLDEN_PARAMS, "vnp_SecureHash": digest}, GOLDEN_SECRET))
        self.assertFalse(
            verify_vnpay(
                {**GOLDEN_PARAMS, "vnp_Amount": "15000001", "vnp_SecureHash": digest},
                GOLDEN_SECRET,
            )
        )


VNPAY_SETTINGS = {
    **TEST_SETTINGS,
    "PAYMENT_PROVIDER": "vnpay",
    "VNPAY_TMN_CODE": "TESTTMN",
    "VNPAY_HASH_SECRET": GOLDEN_SECRET,
    "VNPAY_PAY_URL": "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html",
    "VNPAY_RETURN_URL": "http://localhost:5173",
}


@override_settings(**VNPAY_SETTINGS)
class VNPayCheckoutTests(PaymentFlowMixin, APITestCase):
    def test_checkout_url_scales_amount_and_returns_to_booking_page(self):
        booking = self.new_booking()
        payment, _ = services.create_payment(booking)
        Payment.objects.filter(pk=payment.pk).update(amount=150000)
        payment.refresh_from_db()
        url = VNPayGateway.checkout_url(payment, "127.0.0.1")
        self.assertIn("vnp_Amount=15000000", url)
        self.assertIn(f"%2Fbookings%2F{booking.code}", url)
        self.assertNotIn("/payments/webhook/", url)
        self.client.force_authenticate(self.alice)
        res = self.client.post(reverse("booking-pay", kwargs={"code": booking.code}))
        self.assertIn("vnp_Amount=", res.data["payment_url"])
        self.assertNotIn("/mock-gateway/", res.data["payment_url"])


def signed_ipn(payment, **overrides):
    params = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": "TESTTMN",
        "vnp_TxnRef": payment.txn_ref,
        "vnp_Amount": str(payment.amount * 100),
        "vnp_ResponseCode": "00",
        "vnp_TransactionStatus": "00",
        "vnp_TransactionNo": "GW1",
        "vnp_OrderInfo": "Booking",
    }
    params.update(overrides)
    params["vnp_SecureHash"] = sign_vnpay(params, GOLDEN_SECRET)
    return params


@override_settings(**VNPAY_SETTINGS)
class VNPayIPNTests(PaymentFlowMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.booking = self.new_booking()
        self.payment, _ = services.create_payment(self.booking)
        self.url = reverse("payment-webhook-vnpay")

    def post_ipn(self, params, **extra):
        return self.client.post(self.url, params, **extra)

    def test_rejects_ip_outside_allowlist_before_touching_payment(self):
        with override_settings(PAYMENT_IPN_IP_ALLOWLIST=["198.51.100.1"]):
            res = self.post_ipn(
                {"vnp_SecureHash": "deadbeef"}, REMOTE_ADDR="203.0.113.5"
            )
        self.assertEqual(res.status_code, 403)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PENDING)

    def test_empty_allowlist_does_not_block(self):
        res = self.post_ipn(signed_ipn(self.payment))
        self.assertNotEqual(res.status_code, 403)

    def test_bad_hash_is_97_and_leaves_payment(self):
        params = signed_ipn(self.payment)
        params["vnp_SecureHash"] = "0" * 128
        res = self.post_ipn(params)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["RspCode"], "97")
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PENDING)

    def test_unknown_txn_is_01(self):
        ghost = Payment(txn_ref="b" * 32, amount=1000)
        res = self.post_ipn(signed_ipn(ghost))
        self.assertEqual(res.data["RspCode"], "01")

    @patch("apps.payments.services.send_booking_confirmation_email")
    def test_success_confirms_once_and_duplicate_is_02(self, email):
        with self.captureOnCommitCallbacks(execute=True):
            first = self.post_ipn(signed_ipn(self.payment))
        second = self.post_ipn(signed_ipn(self.payment))
        self.assertEqual(first.data["RspCode"], "00")
        self.assertEqual(second.data["RspCode"], "02")
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(Payment.objects.filter(status=Payment.Status.SUCCEEDED).count(), 1)
        email.delay.assert_called_once()

    def test_failed_ipn_allows_a_new_payment(self):
        res = self.post_ipn(signed_ipn(
            self.payment, vnp_ResponseCode="24", vnp_TransactionStatus="02"
        ))
        self.assertEqual(res.data["RspCode"], "00")
        self.payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.FAILED)
        self.assertEqual(self.booking.status, Booking.Status.PENDING)
        again, created = services.create_payment(self.booking)
        self.assertTrue(created)
        self.assertNotEqual(again.txn_ref, self.payment.txn_ref)

    def test_success_after_cancel_is_needs_review_without_email(self):
        Payment.objects.filter(pk=self.payment.pk).update(status=Payment.Status.CANCELLED)
        with self.captureOnCommitCallbacks(execute=True):
            res = self.post_ipn(signed_ipn(self.payment))
        self.assertEqual(res.data["RspCode"], "00")
        self.assertNotIn("04", res.content.decode())
        self.payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.NEEDS_REVIEW)
        self.assertEqual(self.booking.status, Booking.Status.PENDING)
        self.assertEqual(len(mail.outbox), 0)

    def test_amount_mismatch_is_00_not_04(self):
        res = self.post_ipn(signed_ipn(self.payment, vnp_Amount=str(self.payment.amount * 100 - 100)))
        self.assertEqual(res.data["RspCode"], "00")
        self.assertNotEqual(res.data["RspCode"], "04")
        self.payment.refresh_from_db()
        self.assertTrue(self.payment.failure_reason.startswith("amount_mismatch"))

    @patch("apps.payments.views.services.process_payment_result", side_effect=RuntimeError("boom"))
    def test_exception_before_commit_is_99(self, _process):
        res = self.post_ipn(signed_ipn(self.payment))
        self.assertEqual(res.data["RspCode"], "99")
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PENDING)

    @patch("apps.payments.services.send_booking_confirmation_email")
    def test_get_ipn_confirms_booking(self, email):
        params = signed_ipn(self.payment)
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.get(self.url, params)
        self.assertEqual(res.data["RspCode"], "00")
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CONFIRMED)
        email.delay.assert_called_once()


QUERY_GOLDEN = {
    "vnp_RequestId": "REQ1",
    "vnp_Version": "2.1.0",
    "vnp_Command": "querydr",
    "vnp_TmnCode": "TESTTMN",
    "vnp_TxnRef": "a" * 32,
    "vnp_TransactionDate": "20261002120000",
    "vnp_CreateDate": "20261002120100",
    "vnp_IpAddr": "127.0.0.1",
    "vnp_OrderInfo": "query",
}
QUERY_GOLDEN_HASH = (
    "9c0d06332e48cd246686af119106fb4d9c2ca6d8eaa2e25a1fb615dceb661a70"
    "085a22fbae348b69fb374a6ce9d18da735bbb697196dd5ee462ad62c581a1654"
)


class VNPayQuerySignTests(SimpleTestCase):
    def test_sign_querydr_matches_golden_vector(self):
        self.assertEqual(sign_querydr(QUERY_GOLDEN, GOLDEN_SECRET), QUERY_GOLDEN_HASH)


class _Body:
    def __init__(self, payload, status=200):
        self.status = status
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@override_settings(**VNPAY_SETTINGS)
class VNPayQueryTests(PaymentFlowMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.booking = self.new_booking()
        self.payment, _ = services.create_payment(self.booking)
        Payment.objects.filter(pk=self.payment.pk).update(amount=150000)
        self.payment.refresh_from_db()

    def test_query_posts_querydr_and_converts_amount(self):
        body = _Body({
            "vnp_ResponseCode": "00",
            "vnp_TransactionStatus": "00",
            "vnp_Amount": "15000000",
            "vnp_TransactionNo": "GW9",
        })
        with patch("urllib.request.urlopen", return_value=body) as opened:
            snapshot = VNPayGateway.query(self.payment)
        sent = json.loads(opened.call_args.args[0].data)
        self.assertEqual(sent["vnp_Command"], "querydr")
        self.assertEqual(sent["vnp_TxnRef"], self.payment.txn_ref)
        self.assertEqual(sent["vnp_SecureHash"], sign_querydr(sent, GOLDEN_SECRET))
        self.assertTrue(snapshot.paid)
        self.assertEqual(snapshot.amount, 150000)
        self.assertEqual(snapshot.gateway_txn_id, "GW9")

    def test_network_error_leaves_payment_pending(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
            self.assertIsNone(services.apply_gateway_query(self.payment))
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PENDING)

    def test_unpaid_pending_booking_is_left_alone(self):
        body = _Body({"vnp_ResponseCode": "00", "vnp_TransactionStatus": "01", "vnp_Amount": "15000000"})
        with patch("urllib.request.urlopen", return_value=body):
            self.assertIsNone(services.apply_gateway_query(self.payment))
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PENDING)

    def test_unpaid_expired_booking_marks_payment_failed(self):
        Booking.objects.filter(pk=self.booking.pk).update(
            status=Booking.Status.EXPIRED, expires_at=timezone.now() - timedelta(seconds=5)
        )
        body = _Body({"vnp_ResponseCode": "00", "vnp_TransactionStatus": "01"})
        with patch("urllib.request.urlopen", return_value=body):
            services.apply_gateway_query(self.payment)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.FAILED)
        self.assertEqual(self.payment.failure_reason, "not_paid_at_gateway")

    @patch("apps.payments.services.send_booking_confirmation_email")
    def test_paid_cancelled_payment_needs_review(self, email):
        Payment.objects.filter(pk=self.payment.pk).update(status=Payment.Status.CANCELLED)
        self.payment.refresh_from_db()
        body = _Body({
            "vnp_ResponseCode": "00",
            "vnp_TransactionStatus": "00",
            "vnp_Amount": "15000000",
            "vnp_TransactionNo": "GW9",
        })
        with patch("urllib.request.urlopen", return_value=body):
            services.apply_gateway_query(self.payment)
        self.payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.NEEDS_REVIEW)
        self.assertNotEqual(self.booking.status, Booking.Status.CONFIRMED)
        email.delay.assert_not_called()


@override_settings(**VNPAY_SETTINGS)
class ReconcileScheduleTests(PaymentFlowMixin, APITestCase):
    def test_only_stale_pending_vnpay_payments_are_selected(self):
        a2, a3 = seat(self.showtime, "A", 2), seat(self.showtime, "A", 3)
        alice_booking = self.new_booking(self.a1)
        stale, _ = services.create_payment(alice_booking)
        cancelled = Payment.objects.create(
            booking=alice_booking,
            amount=1,
            provider=Payment.Provider.VNPAY,
            status=Payment.Status.CANCELLED,
        )
        bob_booking = booking_services.hold_seats(
            user=self.bob, showtime=self.showtime, seat_ids=[a2.id]
        )
        Payment.objects.create(
            booking=bob_booking,
            amount=1,
            provider=Payment.Provider.VNPAY,
            status=Payment.Status.PENDING,
        )
        carol = User.objects.create(username="carol", email="carol@example.com")
        carol_booking = booking_services.hold_seats(
            user=carol, showtime=self.showtime, seat_ids=[a3.id]
        )
        mock_old = Payment.objects.create(
            booking=carol_booking,
            amount=1,
            provider=Payment.Provider.MOCK,
            status=Payment.Status.PENDING,
        )
        old = timezone.now() - timedelta(seconds=180)
        Payment.objects.filter(pk__in=[stale.pk, mock_old.pk, cancelled.pk]).update(created_at=old)
        due = list(services.payments_due_for_reconcile(timezone.now()))
        self.assertEqual([payment.pk for payment in due], [stale.pk])
        with patch("apps.payments.tasks.apply_gateway_query") as query:
            from .tasks import reconcile_pending_payments
            reconcile_pending_payments()
        query.assert_called_once()
        self.assertEqual(query.call_args.args[0].pk, stale.pk)

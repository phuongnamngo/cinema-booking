import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.bookings import services as booking_services
from apps.bookings.holds import get_redis, hold_key
from apps.bookings.models import Booking, BookingSeat
from apps.bookings.tasks import send_booking_confirmation_email
from apps.bookings.tests import TEST_CHANNEL_LAYERS, TEST_REDIS_URL, build_showtime, seat
from apps.users.models import User

from . import gateways, services
from .models import Payment

TEST_SETTINGS = dict(
    REDIS_URL=TEST_REDIS_URL,
    CHANNEL_LAYERS=TEST_CHANNEL_LAYERS,
    PAYMENT_WEBHOOK_SECRET="test-secret",
    PAYMENT_MOCK_ENABLED=True,
)


class PaymentFlowMixin:
    def setUp(self):
        get_redis().flushdb()
        self.alice = User.objects.create(username="alice", email="alice@example.com")
        self.bob = User.objects.create(username="bob", email="bob@example.com")
        self.showtime = build_showtime()
        self.a1, self.b1 = seat(self.showtime, "A", 1), seat(self.showtime, "B", 1)
        self.webhook_url = reverse("payment-webhook-mock")

    def tearDown(self):
        get_redis().flushdb()

    def new_booking(self, *seats, user=None):
        seats = seats or (self.a1, self.b1)
        return booking_services.hold_seats(
            user=user or self.alice, showtime=self.showtime, seat_ids=[s.id for s in seats]
        )

    @staticmethod
    def signed(payment, result="success", amount=None):
        body = json.dumps({
            "txn_ref": payment.txn_ref,
            "gateway_txn_id": "GW123",
            "amount": payment.amount if amount is None else amount,
            "result": result,
        }).encode()
        return body, gateways.sign(body)

    def send_webhook(self, payment, **kwargs):
        body, sig = self.signed(payment, **kwargs)
        return self.client.post(
            self.webhook_url, data=body, content_type="application/json", HTTP_X_SIGNATURE=sig
        )


@override_settings(**TEST_SETTINGS)
class CreatePaymentTests(PaymentFlowMixin, APITestCase):
    def pay_url(self, booking):
        return reverse("booking-pay", kwargs={"code": booking.code})

    def test_create_returns_amount_from_server_and_gateway_url(self):
        booking = self.new_booking()
        self.client.force_authenticate(self.alice)
        res = self.client.post(self.pay_url(booking))
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["amount"], 80000 + 100000)   # A1 thường + B1 VIP
        self.assertIn(f"/mock-gateway/{res.data['txn_ref']}/", res.data["payment_url"])

    def test_create_is_idempotent(self):
        booking = self.new_booking()
        self.client.force_authenticate(self.alice)
        first = self.client.post(self.pay_url(booking))
        second = self.client.post(self.pay_url(booking))
        self.assertEqual((first.status_code, second.status_code), (201, 200))
        self.assertEqual(first.data["txn_ref"], second.data["txn_ref"])
        self.assertEqual(Payment.objects.count(), 1)

    def test_cannot_pay_someone_elses_booking(self):
        booking = self.new_booking()
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.post(self.pay_url(booking)).status_code, 404)

    def test_requires_login(self):
        booking = self.new_booking()
        self.assertEqual(self.client.post(self.pay_url(booking)).status_code, 401)

    def test_cannot_pay_non_pending_booking(self):
        booking = self.new_booking()
        Booking.objects.filter(pk=booking.pk).update(status=Booking.Status.CANCELLED)
        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.post(self.pay_url(booking)).status_code, 409)

    def test_cannot_start_payment_when_booking_is_about_to_expire(self):
        booking = self.new_booking()
        Booking.objects.filter(pk=booking.pk).update(expires_at=timezone.now() + timedelta(seconds=30))
        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.post(self.pay_url(booking)).status_code, 400)


@override_settings(**TEST_SETTINGS)
class WebhookTests(PaymentFlowMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.booking = self.new_booking()
        self.payment, _ = services.create_payment(self.booking)

    def test_rejects_missing_wrong_and_tampered_signature(self):
        body, sig = self.signed(self.payment)
        post = lambda **extra: self.client.post(
            self.webhook_url, data=body, content_type="application/json", **extra
        )
        self.assertEqual(post().status_code, 401)                            # thiếu chữ ký
        self.assertEqual(post(HTTP_X_SIGNATURE="0" * 64).status_code, 401)   # sai chữ ký
        tampered = body.replace(b'"success"', b'"failed" ')                  # đổi nội dung, giữ chữ ký cũ
        res = self.client.post(
            self.webhook_url, data=tampered, content_type="application/json", HTTP_X_SIGNATURE=sig
        )
        self.assertEqual(res.status_code, 401)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PENDING)

    def test_signed_but_malformed_payload_is_400(self):
        body = b'{"txn_ref": "x"}'
        res = self.client.post(
            self.webhook_url, data=body, content_type="application/json",
            HTTP_X_SIGNATURE=gateways.sign(body),
        )
        self.assertEqual(res.status_code, 400)

    @patch("apps.bookings.realtime.broadcast_seats")
    @patch("apps.payments.services.send_booking_confirmation_email")
    def test_success_confirms_booking_and_notifies(self, email, broadcast):
        with self.captureOnCommitCallbacks(execute=True):
            res = self.send_webhook(self.payment)

        self.assertEqual((res.status_code, res.data["status"]), (200, "confirmed"))
        self.booking.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(self.payment.status, Payment.Status.SUCCEEDED)
        self.assertEqual(self.payment.gateway_txn_id, "GW123")
        self.assertIsNotNone(self.payment.paid_at)
        # Ghế vẫn bị chốt vĩnh viễn (sold), khóa Redis đã được nhả
        self.assertEqual(BookingSeat.objects.filter(booking=self.booking, is_active=True).count(), 2)
        self.assertFalse(get_redis().exists(hold_key(self.showtime.id, self.a1.id)))
        broadcast.assert_called_once_with(
            self.showtime.id, "seats_sold", sorted([self.a1.id, self.b1.id])
        )
        email.delay.assert_called_once_with(self.booking.id)

    @patch("apps.bookings.realtime.broadcast_seats")
    @patch("apps.payments.services.send_booking_confirmation_email")
    def test_duplicate_webhook_is_idempotent(self, email, broadcast):
        with self.captureOnCommitCallbacks(execute=True):
            first = self.send_webhook(self.payment)
            second = self.send_webhook(self.payment)
            third = self.send_webhook(self.payment)

        self.assertEqual([r.data["status"] for r in (first, second, third)],
                         ["confirmed", "duplicate", "duplicate"])
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.SUCCEEDED)   # không bị ghi đè
        email.delay.assert_called_once()
        broadcast.assert_called_once()

    def test_failed_result_keeps_booking_pending_and_allows_retry(self):
        res = self.send_webhook(self.payment, result="failed")
        self.assertEqual(res.data["status"], "failed")
        self.payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.FAILED)
        self.assertEqual(self.booking.status, Booking.Status.PENDING)

        retry, created = services.create_payment(self.booking)
        self.assertTrue(created)
        self.assertNotEqual(retry.txn_ref, self.payment.txn_ref)

    def test_amount_mismatch_is_not_confirmed(self):
        res = self.send_webhook(self.payment, amount=self.payment.amount - 1000)
        self.assertEqual(res.data["status"], "needs_review")
        self.payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.NEEDS_REVIEW)
        self.assertIn("amount_mismatch", self.payment.failure_reason)
        self.assertEqual(self.booking.status, Booking.Status.PENDING)

    def test_payment_after_expiry_needs_review(self):
        Booking.objects.filter(pk=self.booking.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        booking_services.expire_pending_bookings()   # Celery/lazy đã dọn xong, ghế đã nhả

        res = self.send_webhook(self.payment)
        self.assertEqual(res.data["status"], "needs_review")
        self.payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.NEEDS_REVIEW)
        self.assertEqual(self.booking.status, Booking.Status.EXPIRED)   # không "hồi sinh" đơn

    def test_unknown_txn_ref_is_acknowledged(self):
        ghost = Payment(txn_ref="f" * 32, amount=1000)   # chưa lưu DB
        res = self.send_webhook(ghost)
        self.assertEqual((res.status_code, res.data["status"]), (200, "ignored"))

    @patch("apps.bookings.realtime.broadcast_seats")
    @patch("apps.payments.services.send_booking_confirmation_email")
    def test_confirmed_seats_show_as_sold_and_cannot_be_rebooked(self, email, broadcast):
        self.send_webhook(self.payment)
        self.client.force_authenticate(self.bob)
        res = self.client.post(
            reverse("showtime-hold", args=[self.showtime.id]),
            {"seat_ids": [self.a1.id]}, format="json",
        )
        self.assertEqual(res.status_code, 409)
        seats = self.client.get(reverse("showtime-seats", args=[self.showtime.id])).data
        self.assertEqual({s["label"]: s["status"] for s in seats}["A1"], "sold")


@override_settings(**TEST_SETTINGS)
class MockGatewayTests(PaymentFlowMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.booking = self.new_booking()
        self.payment, _ = services.create_payment(self.booking)
        self.url = reverse("mock-gateway", args=[self.payment.txn_ref])

    @patch("apps.bookings.realtime.broadcast_seats")
    @patch("apps.payments.services.send_booking_confirmation_email")
    def test_gateway_page_confirms_booking(self, email, broadcast):
        self.assertEqual(self.client.get(self.url).status_code, 200)
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post(self.url, {"result": "success"})
        self.assertEqual(res.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CONFIRMED)

    def test_gateway_rejects_unknown_result(self):
        self.assertEqual(self.client.post(self.url, {"result": "hack"}).status_code, 400)

    @override_settings(PAYMENT_MOCK_ENABLED=False)
    def test_gateway_is_hidden_when_disabled(self):
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, {"result": "success"}).status_code, 404)


@override_settings(**TEST_SETTINGS)
class TicketTests(PaymentFlowMixin, APITestCase):
    def test_qr_only_for_confirmed_booking_of_owner(self):
        booking = self.new_booking()
        url = reverse("booking-qr", kwargs={"code": booking.code})

        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.get(url).status_code, 404)   # còn pending

        Booking.objects.filter(pk=booking.pk).update(status=Booking.Status.CONFIRMED)
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "image/svg+xml")
        self.assertIn(b"<svg", res.content)

        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.get(url).status_code, 404)   # không phải của bob


@override_settings(**TEST_SETTINGS)
class ConfirmationEmailTests(PaymentFlowMixin, TestCase):
    def test_email_only_for_confirmed_booking(self):
        booking = self.new_booking()
        send_booking_confirmation_email(booking.id)
        self.assertEqual(len(mail.outbox), 0)   # đơn còn pending: không gửi

        Booking.objects.filter(pk=booking.pk).update(status=Booking.Status.CONFIRMED)
        send_booking_confirmation_email(booking.id)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["alice@example.com"])
        self.assertIn(booking.code, message.body)
        self.assertIn("A1", message.body)

    def test_deleted_booking_is_ignored(self):
        send_booking_confirmation_email(999999)
        self.assertEqual(len(mail.outbox), 0)


@override_settings(**TEST_SETTINGS)
class ConcurrentWebhookTests(PaymentFlowMixin, TransactionTestCase):
    """TransactionTestCase để các thread thấy dữ liệu đã commit của nhau."""

    @patch("apps.bookings.realtime.broadcast_seats")
    @patch("apps.payments.services.send_booking_confirmation_email")
    def test_parallel_duplicate_webhooks_confirm_exactly_once(self, email, broadcast):
        booking = self.new_booking()
        payment, _ = services.create_payment(booking)
        body, sig = self.signed(payment)

        broadcast.reset_mock()

        def attempt(_):
            try:
                res = APIClient().post(
                    self.webhook_url, data=body, content_type="application/json",
                    HTTP_X_SIGNATURE=sig,
                )
                return res.data["status"]
            finally:
                connection.close()   # mỗi thread có kết nối DB riêng

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, range(8)))

        self.assertEqual(sorted(results), ["confirmed"] + ["duplicate"] * 7)
        self.assertEqual(Payment.objects.filter(status=Payment.Status.SUCCEEDED).count(), 1)
        email.delay.assert_called_once_with(booking.id)
        broadcast.assert_called_once()
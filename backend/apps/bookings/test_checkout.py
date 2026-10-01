from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.db import connection
from django.test import TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.payments.models import Payment
from apps.payments.tests import TEST_SETTINGS, PaymentFlowMixin
from apps.promotions.models import Combo, Voucher
from apps.users.models import User

from .models import Booking, BookingCombo, BookingSeat
from .tasks import send_booking_confirmation_email
from .tests import build_showtime, seat

PASSWORD = "Str0ng!Pass_123"
CHECKOUT_SETTINGS = dict(MIN_PAYABLE_AMOUNT=1000)


def make_booking(
    user,
    showtime,
    seats,
    *,
    status=Booking.Status.PENDING,
    expires_in=timedelta(minutes=10),
):
    """Tạo đơn trực tiếp bằng ORM (không qua Redis) để test tập trung vào phần checkout."""
    prices = [showtime.price_for(s.seat_type) for s in seats]
    booking = Booking.objects.create(
        user=user,
        showtime=showtime,
        status=status,
        total_amount=sum(prices),
        expires_at=timezone.now() + expires_in,
    )
    BookingSeat.objects.bulk_create(
        [
            BookingSeat(booking=booking, showtime=showtime, seat=s, price=p)
            for s, p in zip(seats, prices)
        ]
    )
    return booking


class CheckoutMixin:
    def setUp(self):
        self.alice = User.objects.create_user("alice", "alice@example.com", PASSWORD)
        self.bob = User.objects.create_user("bob", "bob@example.com", PASSWORD)
        self.carol = User.objects.create_user("carol", "carol@example.com", PASSWORD)
        self.showtime = build_showtime()  # A1-A3 thường 80.000, B1-B3 VIP 100.000
        self.a1, self.a2, self.a3 = (seat(self.showtime, "A", n) for n in (1, 2, 3))
        self.b1, self.b2, self.b3 = (seat(self.showtime, "B", n) for n in (1, 2, 3))

        self.popcorn = Combo.objects.create(name="Combo Bắp Nước", price=79000)
        self.drink = Combo.objects.create(name="Nước ngọt", price=25000)
        self.retired = Combo.objects.create(
            name="Combo cũ", price=50000, is_active=False
        )
        self.welcome = Voucher.objects.create(
            code="WELCOME10",
            discount_type="percent",
            value=10,
            max_discount=30000,
            min_order_amount=100000,
        )
        self.save20k = Voucher.objects.create(
            code="SAVE20K",
            discount_type="fixed",
            value=20000,
            min_order_amount=150000,
        )
        self.booking = make_booking(
            self.alice, self.showtime, [self.a1, self.b1]
        )  # 180.000

    def url(self, name, booking=None):
        return reverse(name, kwargs={"code": (booking or self.booking).code})

    def put_combos(self, *lines, booking=None, user=None):
        self.client.force_authenticate(user or self.alice)
        items = [{"combo": combo.id, "quantity": qty} for combo, qty in lines]
        return self.client.put(
            self.url("booking-combos", booking), {"items": items}, format="json"
        )

    def put_voucher(self, code, booking=None, user=None):
        self.client.force_authenticate(user or self.alice)
        return self.client.put(
            self.url("booking-voucher", booking), {"code": code}, format="json"
        )

    def delete_voucher(self, booking=None, user=None):
        self.client.force_authenticate(user or self.alice)
        return self.client.delete(self.url("booking-voucher", booking))


@override_settings(**CHECKOUT_SETTINGS)
class ComboCheckoutTests(CheckoutMixin, APITestCase):
    def test_set_combos_recomputes_totals_on_server(self):
        res = self.put_combos((self.popcorn, 2), (self.drink, 1))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["seats_amount"], 180000)
        self.assertEqual(res.data["combos_amount"], 2 * 79000 + 25000)
        self.assertEqual(res.data["total_amount"], 180000 + 183000)
        self.assertEqual(len(res.data["combos"]), 2)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.total_amount, 363000)

    def test_put_replaces_everything_and_is_idempotent(self):
        first = self.put_combos((self.popcorn, 2))
        again = self.put_combos((self.popcorn, 2))
        self.assertEqual(first.data["total_amount"], again.data["total_amount"])
        self.assertEqual(self.booking.combo_lines.count(), 1)

        cleared = self.put_combos()  # danh sách rỗng = bỏ hết combo
        self.assertEqual(cleared.data["total_amount"], 180000)
        self.assertEqual(self.booking.combo_lines.count(), 0)

    def test_duplicate_lines_are_merged_then_capped(self):
        res = self.put_combos((self.popcorn, 1), (self.popcorn, 2))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            [(c["combo"], c["quantity"]) for c in res.data["combos"]],
            [(self.popcorn.id, 3)],
        )
        self.assertEqual(
            self.put_combos((self.popcorn, 6), (self.popcorn, 6)).status_code, 400
        )

    def test_rejects_unknown_retired_and_invalid_lines(self):
        self.assertEqual(self.put_combos((self.retired, 1)).status_code, 400)
        self.assertEqual(self.put_combos((self.popcorn, 0)).status_code, 400)
        self.client.force_authenticate(self.alice)
        res = self.client.put(
            self.url("booking-combos"),
            {"items": [{"combo": 999999, "quantity": 1}]},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_price_is_snapshotted_until_the_next_edit(self):
        self.put_combos((self.popcorn, 1))
        Combo.objects.filter(pk=self.popcorn.pk).update(price=99000)
        self.assertEqual(
            self.booking.combo_lines.get().unit_price, 79000
        )  # đơn không bị đổi giá
        res = self.put_combos(
            (self.popcorn, 1)
        )  # sửa đơn thì chốt lại theo giá hiện tại
        self.assertEqual(res.data["combos_amount"], 99000)

    def test_only_the_owner_can_edit(self):
        self.assertEqual(
            self.put_combos((self.popcorn, 1), user=self.bob).status_code, 404
        )
        self.assertEqual(self.put_voucher("WELCOME10", user=self.bob).status_code, 404)

    def test_cannot_edit_a_booking_that_is_not_pending(self):
        Booking.objects.filter(pk=self.booking.pk).update(
            status=Booking.Status.CONFIRMED
        )
        self.assertEqual(self.put_combos((self.popcorn, 1)).status_code, 409)
        self.assertEqual(self.put_voucher("WELCOME10").status_code, 409)

    def test_cannot_edit_an_expired_booking(self):
        Booking.objects.filter(pk=self.booking.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertEqual(self.put_combos((self.popcorn, 1)).status_code, 409)


@override_settings(**CHECKOUT_SETTINGS)
class VoucherCheckoutTests(CheckoutMixin, APITestCase):
    def test_percent_voucher_and_code_normalisation(self):
        res = self.put_voucher("  welcome10 ")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["voucher_code"], "WELCOME10")
        self.assertEqual(res.data["discount_amount"], 18000)
        self.assertEqual(res.data["total_amount"], 162000)

    def test_discount_is_recomputed_when_combos_change(self):
        self.put_voucher("WELCOME10")
        res = self.put_combos(
            (self.popcorn, 2)
        )  # subtotal 338.000: 10% = 33.800, chặn ở 30.000
        self.assertEqual(res.data["discount_amount"], 30000)
        self.assertEqual(res.data["total_amount"], 338000 - 30000)

    def test_fixed_voucher(self):
        res = self.put_voucher("SAVE20K")
        self.assertEqual(
            (res.data["discount_amount"], res.data["total_amount"]), (20000, 160000)
        )

    def test_minimum_order_is_enforced_when_applying(self):
        small = make_booking(self.bob, self.showtime, [self.a2])  # 80.000 < 150.000
        res = self.put_voucher("SAVE20K", booking=small, user=self.bob)
        self.assertEqual(res.status_code, 400)
        self.assertIn("tối thiểu", str(res.data["code"]))
        small.refresh_from_db()
        self.assertIsNone(small.voucher_id)

    def test_removing_combos_below_the_minimum_is_rejected_and_rolled_back(self):
        small = make_booking(self.bob, self.showtime, [self.a2])  # 80.000
        self.put_combos((self.popcorn, 1), booking=small, user=self.bob)  # 159.000
        self.assertEqual(
            self.put_voucher("SAVE20K", booking=small, user=self.bob).status_code, 200
        )

        res = self.put_combos(
            booking=small, user=self.bob
        )  # bỏ combo -> 80.000 < 150.000
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            small.combo_lines.count(), 1
        )  # combo cũ còn nguyên (đã rollback)
        small.refresh_from_db()
        self.assertEqual(small.total_amount, 159000 - 20000)

    def test_unknown_and_disabled_codes_look_the_same(self):
        now = timezone.now()
        Voucher.objects.create(
            code="OFF", discount_type="fixed", value=1000, is_active=False
        )
        Voucher.objects.create(
            code="FUTURE",
            discount_type="fixed",
            value=1000,
            valid_from=now + timedelta(days=1),
        )
        Voucher.objects.create(
            code="PAST",
            discount_type="fixed",
            value=1000,
            valid_until=now - timedelta(days=1),
        )
        messages = {}
        for code in ("NOPE", "OFF", "FUTURE", "PAST"):
            res = self.put_voucher(code)
            self.assertEqual(res.status_code, 400, code)
            messages[code] = str(res.data["code"])
        # Không lộ mã nào đang tồn tại: mã sai và mã đã tắt trả cùng một thông báo
        self.assertEqual(messages["NOPE"], messages["OFF"])
        self.assertIn("chưa", messages["FUTURE"])
        self.assertIn("hết hạn", messages["PAST"])

    def test_usage_limit_is_derived_from_live_bookings(self):
        Voucher.objects.create(
            code="FLASH50",
            discount_type="percent",
            value=50,
            max_discount=50000,
            usage_limit=2,
        )
        b_bob = make_booking(self.bob, self.showtime, [self.a2])
        b_carol = make_booking(self.carol, self.showtime, [self.a3])

        self.assertEqual(
            self.put_voucher("FLASH50").status_code, 200
        )  # alice (self.booking)
        self.assertEqual(
            self.put_voucher("FLASH50", booking=b_bob, user=self.bob).status_code, 200
        )
        res = self.put_voucher("FLASH50", booking=b_carol, user=self.carol)
        self.assertEqual(res.status_code, 400)
        self.assertIn("hết lượt", str(res.data["code"]))

        # Đơn của alice quá hạn giữ ghế (Celery chưa kịp dọn): lượt dùng được trả lại ngay
        Booking.objects.filter(pk=self.booking.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertEqual(
            self.put_voucher("FLASH50", booking=b_carol, user=self.carol).status_code,
            200,
        )

    def test_per_user_limit(self):
        other = build_showtime()
        second = make_booking(
            self.alice, other, [seat(other, "A", 1), seat(other, "B", 1)]
        )
        self.assertEqual(self.put_voucher("WELCOME10").status_code, 200)
        res = self.put_voucher("WELCOME10", booking=second)
        self.assertEqual(res.status_code, 400)
        self.assertIn("lượt", str(res.data["code"]))

        self.delete_voucher()  # gỡ khỏi đơn đầu thì lượt được trả
        self.assertEqual(self.put_voucher("WELCOME10", booking=second).status_code, 200)

    def test_apply_is_idempotent_replaceable_and_removable(self):
        first = self.put_voucher("WELCOME10")
        again = self.put_voucher("WELCOME10")
        self.assertEqual(first.data["total_amount"], again.data["total_amount"])
        self.assertEqual(Booking.objects.filter(voucher=self.welcome).count(), 1)

        replaced = self.put_voucher("SAVE20K")
        self.assertEqual(replaced.data["voucher_code"], "SAVE20K")
        self.assertEqual(
            Booking.objects.filter(voucher=self.welcome).count(), 0
        )  # lượt cũ tự được trả

        removed = self.delete_voucher()
        self.assertEqual(removed.status_code, 200)
        self.assertIsNone(removed.data["voucher_code"])
        self.assertEqual(
            (removed.data["discount_amount"], removed.data["total_amount"]), (0, 180000)
        )
        self.assertEqual(self.delete_voucher().status_code, 200)  # gỡ lần nữa vẫn ổn

    def test_failed_replace_keeps_the_old_voucher(self):
        self.put_voucher("WELCOME10")
        self.assertEqual(self.put_voucher("NOPE").status_code, 400)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.voucher_id, self.welcome.id)

    def test_order_is_never_free(self):
        Voucher.objects.create(code="FREE", discount_type="fixed", value=1_000_000)
        res = self.put_voucher("FREE")
        self.assertEqual(res.data["total_amount"], 1000)  # MIN_PAYABLE_AMOUNT
        self.assertEqual(res.data["discount_amount"], 179000)

    def test_booking_list_query_count_does_not_grow_with_bookings(self):
        def measure():
            self.client.force_authenticate(self.alice)
            with CaptureQueriesContext(connection) as queries:
                res = self.client.get(reverse("booking-list"))
            self.assertEqual(res.status_code, 200)
            return len(queries), res.data["count"]

        BookingCombo.objects.create(
            booking=self.booking, combo=self.popcorn, quantity=1, unit_price=79000
        )
        queries_before, count_before = measure()

        for s in (self.a2, self.a3, self.b2):
            extra = make_booking(
                self.alice, self.showtime, [s], status=Booking.Status.CONFIRMED
            )
            BookingCombo.objects.create(
                booking=extra, combo=self.drink, quantity=2, unit_price=25000
            )
            Booking.objects.filter(pk=extra.pk).update(voucher=self.welcome)
        queries_after, count_after = measure()

        self.assertEqual((count_before, count_after), (1, 4))
        self.assertEqual(
            queries_before, queries_after
        )  # select_related/prefetch_related đã tải sẵn


@override_settings(**TEST_SETTINGS, MIN_PAYABLE_AMOUNT=1000)
class CheckoutPaymentTests(PaymentFlowMixin, APITestCase):
    """Checkout gặp thanh toán thật: tiền thu phải khớp với đơn."""

    def setUp(self):
        super().setUp()
        self.popcorn = Combo.objects.create(name="Combo Bắp Nước", price=79000)
        self.welcome = Voucher.objects.create(
            code="WELCOME10",
            discount_type="percent",
            value=10,
            max_discount=30000,
            min_order_amount=100000,
        )
        self.booking = self.new_booking()  # A1 + B1 = 180.000 (giữ ghế thật qua Redis)
        self.client.force_authenticate(self.alice)
        self.code = {"code": self.booking.code}

    def checkout(self, quantity=1):
        self.client.put(
            reverse("booking-combos", kwargs=self.code),
            {"items": [{"combo": self.popcorn.id, "quantity": quantity}]},
            format="json",
        )
        return self.client.put(
            reverse("booking-voucher", kwargs=self.code),
            {"code": "WELCOME10"},
            format="json",
        )

    def start_payment(self):
        res = self.client.post(reverse("booking-pay", kwargs=self.code))
        return res, Payment.objects.filter(txn_ref=res.data.get("txn_ref")).first()

    @patch("apps.bookings.realtime.broadcast_seats")
    @patch("apps.payments.services.send_booking_confirmation_email")
    def test_discounted_total_is_charged_and_confirmed(self, email, broadcast):
        # 180.000 + 79.000 = 259.000; giảm 10% = 25.900
        self.assertEqual(self.checkout().data["total_amount"], 233100)

        res, payment = self.start_payment()
        self.assertEqual((res.status_code, res.data["amount"]), (201, 233100))

        with self.captureOnCommitCallbacks(execute=True):
            result = self.send_webhook(payment)
        self.assertEqual(result.data["status"], "confirmed")

        self.booking.refresh_from_db()
        self.assertEqual(
            (self.booking.status, self.booking.total_amount),
            (Booking.Status.CONFIRMED, 233100),
        )
        # Đơn đã thanh toán vẫn chiếm một lượt dùng voucher
        self.assertEqual(
            Booking.objects.filter(
                voucher=self.welcome, status=Booking.Status.CONFIRMED
            ).count(),
            1,
        )

    def test_booking_is_locked_while_a_payment_is_waiting(self):
        self.checkout()
        self.start_payment()
        combos = self.client.put(
            reverse("booking-combos", kwargs=self.code), {"items": []}, format="json"
        )
        remove = self.client.delete(reverse("booking-voucher", kwargs=self.code))
        self.assertEqual((combos.status_code, remove.status_code), (409, 409))

    def test_after_a_failed_payment_the_order_can_be_changed_and_repaid(self):
        _, payment = self.start_payment()
        self.assertEqual(
            self.send_webhook(payment, result="failed").data["status"], "failed"
        )

        res = self.client.put(
            reverse("booking-combos", kwargs=self.code),
            {"items": [{"combo": self.popcorn.id, "quantity": 2}]},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        repay, _ = self.start_payment()
        self.assertEqual(
            (repay.status_code, repay.data["amount"]), (201, 180000 + 2 * 79000)
        )

    @patch("apps.bookings.realtime.broadcast_seats")
    @patch("apps.payments.services.send_booking_confirmation_email")
    def test_total_changed_behind_our_back_needs_review(self, email, broadcast):
        _, payment = self.start_payment()
        # Giả lập lớp 1 bị thủng: tổng đơn bị đổi sau khi giao dịch đã chốt số tiền
        Booking.objects.filter(pk=self.booking.pk).update(total_amount=1000)

        with self.captureOnCommitCallbacks(execute=True):
            res = self.send_webhook(payment)
        self.assertEqual(res.data["status"], "needs_review")
        payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertIn("booking_total_changed", payment.failure_reason)
        self.assertEqual(self.booking.status, Booking.Status.PENDING)
        email.delay.assert_not_called()

    def test_confirmation_email_lists_combos_and_discount(self):
        self.checkout()
        Booking.objects.filter(pk=self.booking.pk).update(
            status=Booking.Status.CONFIRMED
        )
        send_booking_confirmation_email(self.booking.id)
        body = mail.outbox[0].body
        self.assertIn("1x Combo Bắp Nước", body)
        self.assertIn("Giảm giá (WELCOME10): -25.900đ", body)
        self.assertIn("233.100đ", body)


@override_settings(**CHECKOUT_SETTINGS)
class ConcurrentVoucherTests(TransactionTestCase):
    """TransactionTestCase để các thread thấy dữ liệu đã commit của nhau."""

    def test_the_last_use_goes_to_exactly_one_person(self):
        showtime = build_showtime()
        Voucher.objects.create(
            code="LASTONE", discount_type="fixed", value=10000, usage_limit=1
        )
        positions = [("A", 1), ("A", 2), ("A", 3), ("B", 1), ("B", 2), ("B", 3)]
        users = [
            User.objects.create_user(f"u{i}", f"u{i}@example.com", PASSWORD)
            for i in range(6)
        ]
        bookings = [
            make_booking(user, showtime, [seat(showtime, row, number)])
            for user, (row, number) in zip(users, positions)
        ]

        def attempt(pair):
            user, booking = pair
            try:
                client = APIClient()
                client.force_authenticate(user)
                url = reverse("booking-voucher", kwargs={"code": booking.code})
                return client.put(url, {"code": "LASTONE"}, format="json").status_code
            finally:
                connection.close()  # mỗi thread có kết nối DB riêng

        with ThreadPoolExecutor(max_workers=6) as pool:
            codes = list(pool.map(attempt, zip(users, bookings)))

        self.assertEqual(sorted(codes), [200] + [400] * 5)
        self.assertEqual(Booking.objects.filter(voucher__code="LASTONE").count(), 1)

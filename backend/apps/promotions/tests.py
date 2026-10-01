from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.users.models import User

from .exceptions import VoucherNotApplicable
from .models import Combo, Voucher


@override_settings(MIN_PAYABLE_AMOUNT=1000)
class VoucherRulesTests(SimpleTestCase):
    """Quy tắc thuần: không cần DB nên chạy rất nhanh."""

    def test_percent_rounds_down_and_respects_cap(self):
        voucher = Voucher(discount_type="percent", value=10)
        self.assertEqual(voucher.compute_discount(180000), 18000)
        self.assertEqual(voucher.compute_discount(80999), 8099)  # làm tròn xuống
        capped = Voucher(discount_type="percent", value=10, max_discount=30000)
        self.assertEqual(capped.compute_discount(338000), 30000)

    def test_fixed(self):
        self.assertEqual(
            Voucher(discount_type="fixed", value=20000).compute_discount(180000), 20000
        )

    def test_order_never_drops_below_min_payable(self):
        self.assertEqual(
            Voucher(discount_type="fixed", value=1_000_000).compute_discount(180000),
            179000,
        )
        self.assertEqual(
            Voucher(discount_type="percent", value=100).compute_discount(50000), 49000
        )
        self.assertEqual(
            Voucher(discount_type="fixed", value=5000).compute_discount(500), 0
        )

    def test_usable_window_and_status(self):
        now = timezone.now()
        hour = timedelta(hours=1)
        for voucher in (
            Voucher(is_active=False),
            Voucher(valid_from=now + hour),
            Voucher(valid_until=now - hour),
        ):
            with self.assertRaises(VoucherNotApplicable):
                voucher.check_usable(now)
        Voucher(valid_from=now - hour, valid_until=now + hour).check_usable(
            now
        )  # không raise

    def test_min_order(self):
        voucher = Voucher(min_order_amount=150000)
        voucher.check_min_order(150000)
        with self.assertRaises(VoucherNotApplicable) as caught:
            voucher.check_min_order(149999)
        self.assertIn("150.000đ", str(caught.exception))


class VoucherConstraintTests(TestCase):
    def test_code_is_normalised_on_save(self):
        voucher = Voucher.objects.create(
            code="  save20k ", discount_type="fixed", value=1000
        )
        self.assertEqual(voucher.code, "SAVE20K")

    def test_database_refuses_lowercase_code_even_when_save_is_bypassed(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Voucher.objects.bulk_create(
                [Voucher(code="lower", discount_type="fixed", value=1000)]
            )

    def test_value_range_is_enforced_by_database(self):
        for kwargs in (
            {"discount_type": "percent", "value": 150},
            {"discount_type": "fixed", "value": 0},
        ):
            with self.subTest(**kwargs), self.assertRaises(
                IntegrityError
            ), transaction.atomic():
                Voucher.objects.create(code="BAD", **kwargs)

    def test_validity_window_must_be_ordered(self):
        now = timezone.now()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Voucher.objects.create(
                code="BAD",
                discount_type="fixed",
                value=1000,
                valid_from=now,
                valid_until=now - timedelta(days=1),
            )


class ComboApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "admin1", "admin1@example.com", "Str0ng!Pass_123", role=User.Role.ADMIN
        )
        self.customer = User.objects.create_user(
            "cus1", "cus1@example.com", "Str0ng!Pass_123"
        )
        Combo.objects.create(name="Bắp", price=49000)
        Combo.objects.create(name="Ẩn", price=10000, is_active=False)
        self.payload = {"name": "Nước", "price": 25000}

    def test_public_sees_only_active_combos(self):
        res = self.client.get(reverse("combo-list"))
        self.assertEqual([c["name"] for c in res.data], ["Bắp"])

    def test_admin_sees_all_combos(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(len(self.client.get(reverse("combo-list")).data), 2)

    def test_only_admin_can_write(self):
        url = reverse("combo-list")
        self.assertEqual(
            self.client.post(url, self.payload, format="json").status_code, 401
        )
        self.client.force_authenticate(self.customer)
        self.assertEqual(
            self.client.post(url, self.payload, format="json").status_code, 403
        )
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.client.post(url, self.payload, format="json").status_code, 201
        )

    def test_delete_is_not_allowed(self):
        combo = Combo.objects.get(name="Bắp")
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.client.delete(reverse("combo-detail", args=[combo.id])).status_code,
            405,
        )

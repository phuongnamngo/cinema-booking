from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.bookings.models import Booking, BookingSeat
from apps.promotions.models import Combo

from .models import Payment
from .tests import TEST_SETTINGS, PaymentFlowMixin
from . import services


@override_settings(**TEST_SETTINGS)
class CancelPaymentTests(PaymentFlowMixin, APITestCase):
    def cancel_url(self, booking):
        return reverse("booking-cancel-payment", kwargs={"code": booking.code})

    def test_owner_can_cancel_pending_payment_and_edit_again(self):
        booking = self.new_booking()
        payment, _ = services.create_payment(booking)
        self.client.force_authenticate(self.alice)
        res = self.client.post(self.cancel_url(booking))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["has_pending_payment"])
        self.assertEqual(res.data["status"], Booking.Status.PENDING)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.CANCELLED)
        self.assertTrue(BookingSeat.objects.filter(booking=booking, is_active=True).exists())
        again, created = services.create_payment(booking)
        self.assertTrue(created)
        self.assertNotEqual(again.txn_ref, payment.txn_ref)

    def test_other_user_gets_404_and_anonymous_gets_401(self):
        booking = self.new_booking()
        services.create_payment(booking)
        self.assertEqual(self.client.post(self.cancel_url(booking)).status_code, 401)
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.post(self.cancel_url(booking)).status_code, 404)

    def test_cancel_without_pending_payment_is_409(self):
        booking = self.new_booking()
        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.post(self.cancel_url(booking)).status_code, 409)

    def test_combo_edit_works_after_pending_payment_is_cancelled(self):
        combo = Combo.objects.create(name="Bắp", price=79000)
        booking = self.new_booking()
        services.create_payment(booking)
        self.client.force_authenticate(self.alice)
        self.client.post(self.cancel_url(booking))
        res = self.client.put(
            reverse("booking-combos", kwargs={"code": booking.code}),
            {"items": [{"combo": combo.id, "quantity": 1}]},
            format="json",
        )
        self.assertEqual(res.status_code, 200)

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .admin import PaymentAdmin
from .models import Payment
from .tests import TEST_SETTINGS, PaymentFlowMixin
from . import services

User = get_user_model()


@override_settings(**TEST_SETTINGS)
class PaymentAdminTests(PaymentFlowMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser("root", "root@example.com", "Str0ng!Pass")
        self.client.force_login(self.admin)
        self.booking = self.new_booking()
        self.payment, _ = services.create_payment(self.booking)
        Payment.objects.filter(pk=self.payment.pk).update(
            status=Payment.Status.NEEDS_REVIEW, failure_reason="late_success_after_cancel"
        )
        self.payment.refresh_from_db()
        self.change_url = reverse("admin:payments_payment_change", args=[self.payment.pk])

    def test_first_note_records_reviewer_and_clearing_it_keeps_the_timestamp(self):
        res = self.client.post(self.change_url, {"review_note": "Đã gọi khách"})
        self.assertEqual(res.status_code, 302)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.review_note, "Đã gọi khách")
        self.assertIsNotNone(self.payment.reviewed_at)
        self.assertEqual(self.payment.reviewed_by, self.admin)
        reviewed_at = self.payment.reviewed_at

        self.client.post(self.change_url, {"review_note": ""})
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.review_note, "")
        self.assertEqual(self.payment.reviewed_at, reviewed_at)

    def test_succeeded_payment_ignores_a_posted_note(self):
        Payment.objects.filter(pk=self.payment.pk).update(
            status=Payment.Status.SUCCEEDED, review_note=""
        )
        url = reverse("admin:payments_payment_change", args=[self.payment.pk])
        self.client.post(url, {"review_note": "không được ghi"})
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.review_note, "")

    def test_queue_filter_lists_only_unreviewed_needs_review(self):
        reviewed = Payment.objects.create(
            booking=self.booking,
            amount=1,
            status=Payment.Status.NEEDS_REVIEW,
            review_note="xong",
            reviewed_at=self.payment.created_at,
            reviewed_by=self.admin,
        )
        url = reverse("admin:payments_payment_changelist")
        res = self.client.get(url, {"review": "unreviewed"})
        self.assertContains(res, self.payment.txn_ref)
        self.assertNotContains(res, reviewed.txn_ref)

    def test_admin_has_no_confirm_or_refund_actions(self):
        model_admin = PaymentAdmin(Payment, admin.site)
        self.assertIsNone(model_admin.actions)
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_delete_permission(None))

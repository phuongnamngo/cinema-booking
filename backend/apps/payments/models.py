import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


def new_txn_ref():
    return uuid.uuid4().hex  # mã giao dịch của mình gửi sang cổng (32 ký tự)


class Payment(models.Model):
    class Provider(models.TextChoices):
        MOCK = "mock", "Mock gateway"
        VNPAY = "vnpay", "VNPay"

    class Status(models.TextChoices):
        PENDING = "pending", "Chờ thanh toán"
        SUCCEEDED = "succeeded", "Thành công"
        FAILED = "failed", "Thất bại"
        CANCELLED = "cancelled", "Đã hủy"
        NEEDS_REVIEW = (
            "needs_review",
            "Cần xử lý thủ công",
        )  # tiền đã thu nhưng không xác nhận được đơn

    booking = models.ForeignKey(
        "bookings.Booking", on_delete=models.PROTECT, related_name="payments"
    )
    provider = models.CharField(
        max_length=20, choices=Provider.choices, default=Provider.MOCK
    )
    txn_ref = models.CharField(
        max_length=32, unique=True, default=new_txn_ref, editable=False
    )
    amount = models.PositiveIntegerField()  # VND, lấy từ booking.total_amount
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    gateway_txn_id = models.CharField(
        max_length=64, blank=True
    )  # mã giao dịch phía cổng
    failure_reason = models.CharField(max_length=255, blank=True)
    raw_payload = models.JSONField(
        null=True, blank=True
    )  # webhook đầu tiên, để đối soát

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_payments",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["booking"],
                condition=Q(status="pending"),
                name="one_pending_payment_per_booking",
            ),
            models.UniqueConstraint(
                fields=["booking"],
                condition=Q(status="succeeded"),
                name="one_succeeded_payment_per_booking",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "paid_at"]),
            models.Index(
                fields=["status", "provider", "created_at"],
                name="payment_reconcile_queue",
            ),
        ]

    def __str__(self):
        return f"{self.txn_ref} ({self.status})"

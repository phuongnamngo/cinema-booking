import secrets

from django.conf import settings
from django.db import models
from django.db.models import Q

# Bỏ I, O, 0, 1 vì dễ nhầm khi đọc mã
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_booking_code(length=8):
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Chờ thanh toán"
        CONFIRMED = "confirmed", "Đã xác nhận"
        EXPIRED = "expired", "Hết hạn giữ ghế"
        CANCELLED = "cancelled", "Đã hủy"

    code = models.CharField(
        max_length=12, unique=True, default=generate_booking_code, editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings"
    )
    showtime = models.ForeignKey(
        "showtimes.Showtime", on_delete=models.PROTECT, related_name="bookings"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total_amount = models.PositiveIntegerField(default=0)   # VND
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "expires_at"]),   # quét booking hết hạn
            models.Index(fields=["user", "-created_at"]),    # "vé của tôi"
        ]
        constraints = [
            # Mỗi user chỉ có 1 đơn đang giữ ghế cho mỗi suất chiếu
            models.UniqueConstraint(
                fields=["user", "showtime"],
                condition=Q(status="pending"),
                name="one_pending_booking_per_user_showtime",
            ),
        ]

    def __str__(self):
        return self.code


class BookingSeat(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="items")
    # Denormalize từ booking.showtime để làm partial unique index
    showtime = models.ForeignKey("showtimes.Showtime", on_delete=models.PROTECT, related_name="+")
    seat = models.ForeignKey("cinemas.Seat", on_delete=models.PROTECT, related_name="+")
    price = models.PositiveIntegerField()   # giá chốt tại thời điểm giữ ghế
    # True khi booking là PENDING/CONFIRMED. Chỉ đổi qua services.py
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            # Chốt chặn cuối: một ghế trong một suất chỉ thuộc về 1 booking còn hiệu lực
            models.UniqueConstraint(
                fields=["showtime", "seat"],
                condition=Q(is_active=True),
                name="uniq_active_seat_per_showtime",
            ),
            models.UniqueConstraint(fields=["booking", "seat"], name="uniq_seat_per_booking"),
        ]

    def __str__(self):
        return f"{self.booking_id}:{self.seat_id}"
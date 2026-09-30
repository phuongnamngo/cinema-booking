from datetime import timedelta

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import (
    DateTimeRangeField,
    RangeBoundary,
    RangeOperators,
)
from django.db import models
from django.db.models import F, Func, Q

from apps.cinemas.models import Seat


class TsTzRange(Func):
    """Ghép start/end thành kiểu TSTZRANGE của Postgres."""

    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


class Showtime(models.Model):
    movie = models.ForeignKey("movies.Movie", on_delete=models.PROTECT, related_name="showtimes")
    room = models.ForeignKey("cinemas.Room", on_delete=models.PROTECT, related_name="showtimes")

    start_time = models.DateTimeField()
    end_time = models.DateTimeField(editable=False)   # tự tính, không nhập tay

    # Đơn vị: VND
    price_standard = models.PositiveIntegerField()
    price_vip = models.PositiveIntegerField()
    price_couple = models.PositiveIntegerField()

    is_active = models.BooleanField(default=True)     # False = đã hủy suất chiếu
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_time"]
        indexes = [
            models.Index(fields=["start_time"]),
            models.Index(fields=["movie", "start_time"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")),
                name="showtime_end_after_start",
            ),
            # Cùng phòng, khoảng thời gian không được chồng lấn (bỏ qua suất đã hủy)
            ExclusionConstraint(
                name="showtime_no_overlap_in_room",
                expressions=[
                    (TsTzRange("start_time", "end_time", RangeBoundary()), RangeOperators.OVERLAPS),
                    ("room", RangeOperators.EQUAL),
                ],
                condition=Q(is_active=True),
            ),
        ]

    def save(self, *args, **kwargs):
        self.end_time = self.start_time + timedelta(minutes=self.movie.duration_minutes)
        super().save(*args, **kwargs)

    def price_for(self, seat_type):
        return {
            Seat.SeatType.STANDARD: self.price_standard,
            Seat.SeatType.VIP: self.price_vip,
            Seat.SeatType.COUPLE: self.price_couple,
        }[seat_type]

    def __str__(self):
        return f"{self.movie} @ {self.room} {self.start_time:%d/%m %H:%M}"
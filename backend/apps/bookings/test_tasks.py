from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.users.models import User
from config.celery import app as celery_app

from .models import Booking, BookingSeat
from .tasks import expire_pending_bookings_task
from .tests import build_showtime, seat


class ExpireTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="alice", email="alice@example.com")
        self.showtime = build_showtime()
        self.a1 = seat(self.showtime, "A", 1)

    def make_booking(self, expires_in, status=Booking.Status.PENDING):
        booking = Booking.objects.create(
            user=self.user, showtime=self.showtime, status=status,
            total_amount=80000, expires_at=timezone.now() + expires_in,
        )
        BookingSeat.objects.create(
            booking=booking, showtime=self.showtime, seat=self.a1, price=80000
        )
        return booking

    def run_task(self):
        # Gọi thẳng hàm (không qua broker) và chạy các callback on_commit
        with patch("apps.bookings.realtime.broadcast_seats") as broadcast:
            with self.captureOnCommitCallbacks(execute=True):
                result = expire_pending_bookings_task()
        return result, broadcast

    def test_expires_overdue_pending_booking_and_broadcasts(self):
        booking = self.make_booking(timedelta(seconds=-1))
        result, broadcast = self.run_task()

        self.assertEqual(result, 1)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.EXPIRED)
        self.assertFalse(BookingSeat.objects.filter(booking=booking, is_active=True).exists())
        broadcast.assert_called_once_with(self.showtime.id, "seats_released", [self.a1.id])

    def test_leaves_fresh_booking_alone(self):
        booking = self.make_booking(timedelta(minutes=5))
        result, broadcast = self.run_task()

        self.assertEqual(result, 0)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.PENDING)
        broadcast.assert_not_called()

    def test_never_touches_confirmed_booking(self):
        booking = self.make_booking(timedelta(days=-1), status=Booking.Status.CONFIRMED)
        result, broadcast = self.run_task()

        self.assertEqual(result, 0)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertTrue(BookingSeat.objects.filter(booking=booking, is_active=True).exists())
        broadcast.assert_not_called()

    def test_running_twice_is_idempotent(self):
        self.make_booking(timedelta(seconds=-1))
        first, _ = self.run_task()
        second, broadcast = self.run_task()
        self.assertEqual((first, second), (1, 0))
        broadcast.assert_not_called()   # lần 2 không còn gì để nhả


class BeatScheduleTests(SimpleTestCase):
    def test_every_scheduled_task_is_registered(self):
        # Bắt lỗi gõ sai tên task trong CELERY_BEAT_SCHEDULE (sai thì Beat chạy mà worker bỏ qua, im lặng)
        import apps.bookings.tasks  # noqa: F401
        import apps.users.tasks  # noqa: F401

        for name, entry in settings.CELERY_BEAT_SCHEDULE.items():
            self.assertIn(entry["task"], celery_app.tasks, name)
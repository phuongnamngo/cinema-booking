from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

from . import services

from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.cinemas.models import Cinema, Room, Seat
from apps.cinemas.services import generate_seats
from apps.movies.models import Movie
from apps.showtimes.models import Showtime
from apps.payments.models import Payment
from apps.payments.services import create_payment
from apps.users.models import User

from .holds import get_redis, hold_key
from .models import Booking, BookingSeat

TEST_CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

TEST_REDIS_URL = "redis://redis:6379/15"


def build_showtime(start_in=timedelta(days=1)):
    movie = Movie.objects.create(
        title="Phim A",
        duration_minutes=120,
        release_date="2026-10-01",
        status="now_showing",
    )
    cinema = Cinema.objects.create(name="C1", address="x", city="HCM")
    room = Room.objects.create(cinema=cinema, name="R1")
    generate_seats(
        room, rows=2, seats_per_row=3, vip_rows=["B"]
    )  # A1-A3 thường, B1-B3 VIP
    start = (timezone.now() + start_in).replace(minute=0, second=0, microsecond=0)
    return Showtime.objects.create(
        movie=movie,
        room=room,
        start_time=start,
        price_standard=80000,
        price_vip=100000,
        price_couple=180000,
    )


def seat(showtime, row, number):
    return Seat.objects.get(room=showtime.room, row=row, number=number)


@override_settings(REDIS_URL=TEST_REDIS_URL, CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
class BookingApiTests(APITestCase):
    def setUp(self):
        get_redis().flushdb()
        self.alice = User.objects.create(username="alice", email="alice@example.com")
        self.bob = User.objects.create(username="bob", email="bob@example.com")
        self.showtime = build_showtime()
        self.a1, self.a2, self.a3 = (seat(self.showtime, "A", n) for n in (1, 2, 3))
        self.b1 = seat(self.showtime, "B", 1)
        self.hold_url = reverse("showtime-hold", args=[self.showtime.id])

    def tearDown(self):
        get_redis().flushdb()

    def hold(self, user, *seats):
        self.client.force_authenticate(user)
        return self.client.post(
            self.hold_url, {"seat_ids": [s.id for s in seats]}, format="json"
        )

    def key(self, s):
        return hold_key(self.showtime.id, s.id)

    def test_hold_creates_pending_booking_with_price_snapshot(self):
        res = self.hold(self.alice, self.a1, self.b1)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], "pending")
        self.assertEqual(res.data["total_amount"], 80000 + 100000)
        self.assertEqual(len(res.data["seats"]), 2)
        ttl = get_redis().ttl(self.key(self.a1))
        self.assertTrue(0 < ttl <= settings.SEAT_HOLD_SECONDS)

    def test_second_user_cannot_take_same_seat(self):
        self.assertEqual(self.hold(self.alice, self.a1).status_code, 201)
        self.assertEqual(self.hold(self.bob, self.a1).status_code, 409)
        self.assertEqual(Booking.objects.count(), 1)

    def test_redis_gate_is_all_or_nothing(self):
        # Giả lập người khác vừa giữ a3 (chỉ có trên Redis, chưa kịp ghi DB)
        get_redis().set(self.key(self.a3), "someone-else", ex=600)
        res = self.hold(self.bob, self.a1, self.a2, self.a3)
        self.assertEqual(res.status_code, 409)
        self.assertFalse(get_redis().exists(self.key(self.a1)))
        self.assertFalse(get_redis().exists(self.key(self.a2)))
        self.assertEqual(Booking.objects.count(), 0)

    def test_one_pending_booking_per_user_per_showtime(self):
        self.assertEqual(self.hold(self.alice, self.a1).status_code, 201)
        self.assertEqual(self.hold(self.alice, self.a2).status_code, 409)

    def test_cancel_releases_seats(self):
        code = self.hold(self.alice, self.a1).data["code"]
        self.client.force_authenticate(self.alice)
        # TestCase bọc mỗi test trong 1 transaction nên on_commit không tự chạy
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post(reverse("booking-cancel", kwargs={"code": code}))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "cancelled")
        self.assertFalse(get_redis().exists(self.key(self.a1)))
        self.assertFalse(BookingSeat.objects.filter(is_active=True).exists())
        self.assertEqual(self.hold(self.bob, self.a1).status_code, 201)

    def test_cancel_booking_cancels_its_pending_payment(self):
        code = self.hold(self.alice, self.a1).data["code"]
        booking = Booking.objects.get(code=code)
        payment, _ = create_payment(booking)
        self.client.force_authenticate(self.alice)
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post(reverse("booking-cancel", kwargs={"code": code}))
        self.assertEqual(res.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.CANCELLED)

    def test_expire_pending_booking_leaves_payment_pending(self):
        code = self.hold(self.alice, self.a1).data["code"]
        booking = Booking.objects.get(code=code)
        payment, _ = create_payment(booking)
        Booking.objects.filter(pk=booking.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        services.expire_pending_bookings()
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PENDING)

    def test_cannot_cancel_non_pending_booking(self):
        code = self.hold(self.alice, self.a1).data["code"]
        Booking.objects.filter(code=code).update(status=Booking.Status.CONFIRMED)
        self.client.force_authenticate(self.alice)
        res = self.client.post(reverse("booking-cancel", kwargs={"code": code}))
        self.assertEqual(res.status_code, 409)

    def test_expired_hold_is_lazily_released(self):
        code = self.hold(self.alice, self.a1).data["code"]
        Booking.objects.filter(code=code).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        get_redis().delete(self.key(self.a1))  # giả lập TTL Redis đã hết
        self.assertEqual(self.hold(self.bob, self.a1).status_code, 201)
        self.assertEqual(Booking.objects.get(code=code).status, Booking.Status.EXPIRED)
        self.assertFalse(
            BookingSeat.objects.filter(booking__code=code, is_active=True).exists()
        )

    def test_db_constraint_blocks_double_booking_without_redis(self):
        def new_item(user):
            booking = Booking.objects.create(
                user=user,
                showtime=self.showtime,
                total_amount=80000,
                expires_at=timezone.now() + timedelta(minutes=10),
            )
            return BookingSeat(
                booking=booking, showtime=self.showtime, seat=self.a1, price=80000
            )

        new_item(self.alice).save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            new_item(self.bob).save()

        # Khi bản ghi cũ không còn hiệu lực thì ghế được phép đặt lại
        BookingSeat.objects.update(is_active=False)
        new_item(self.bob).save()

    def test_seat_statuses(self):
        code = self.hold(self.alice, self.a1).data["code"]
        url = reverse("showtime-seats", args=[self.showtime.id])

        def statuses(user):
            self.client.force_authenticate(user)
            return {s["label"]: s["status"] for s in self.client.get(url).data}

        self.assertEqual(statuses(None)["A1"], "held")
        self.assertEqual(statuses(self.bob)["A1"], "held")
        self.assertEqual(statuses(self.alice)["A1"], "mine")
        self.assertEqual(statuses(self.bob)["A2"], "available")

        Booking.objects.filter(code=code).update(status=Booking.Status.CONFIRMED)
        self.assertEqual(statuses(self.alice)["A1"], "sold")
        self.assertEqual(statuses(self.bob)["A1"], "sold")

    def test_cannot_hold_seat_of_another_room(self):
        other = Room.objects.create(cinema=self.showtime.room.cinema, name="R2")
        generate_seats(other, rows=1, seats_per_row=1)
        foreign = Seat.objects.get(room=other)
        self.assertEqual(self.hold(self.alice, foreign).status_code, 400)

    def test_cannot_hold_after_showtime_started(self):
        past = build_showtime(start_in=timedelta(hours=-3))
        self.client.force_authenticate(self.alice)
        res = self.client.post(
            reverse("showtime-hold", args=[past.id]),
            {"seat_ids": [seat(past, "A", 1).id]},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_seat_list_validation(self):
        self.client.force_authenticate(self.alice)
        for ids in ([], [1, 1], list(range(1, 10))):  # rỗng, trùng, quá 8 ghế
            res = self.client.post(self.hold_url, {"seat_ids": ids}, format="json")
            self.assertEqual(res.status_code, 400, ids)

    def test_hold_requires_login(self):
        res = self.client.post(self.hold_url, {"seat_ids": [self.a1.id]}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_users_only_see_their_own_bookings(self):
        code = self.hold(self.alice, self.a1).data["code"]
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.get(reverse("booking-list")).data["count"], 0)
        detail = reverse("booking-detail", kwargs={"code": code})
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.get(reverse("booking-list")).data["count"], 1)
        self.assertEqual(self.client.get(detail).status_code, 200)

    def test_hold_broadcasts_after_commit(self):
        with patch("apps.bookings.realtime.broadcast_seats") as broadcast:
            with self.captureOnCommitCallbacks(execute=True):
                self.hold(self.alice, self.a1, self.a2)
        broadcast.assert_called_once_with(
            self.showtime.id, "seats_held", [self.a1.id, self.a2.id]
        )

    def test_failed_hold_does_not_broadcast(self):
        self.hold(self.alice, self.a1)
        with patch("apps.bookings.realtime.broadcast_seats") as broadcast:
            with self.captureOnCommitCallbacks(execute=True):
                res = self.hold(self.bob, self.a1)
        self.assertEqual(res.status_code, 409)
        broadcast.assert_not_called()

    def test_cancel_broadcasts_release(self):
        code = self.hold(self.alice, self.a1).data["code"]
        self.client.force_authenticate(self.alice)
        with patch("apps.bookings.realtime.broadcast_seats") as broadcast:
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(reverse("booking-cancel", kwargs={"code": code}))
        broadcast.assert_called_once_with(
            self.showtime.id, "seats_released", [self.a1.id]
        )

    def test_lazy_expiry_broadcasts_release(self):
        code = self.hold(self.alice, self.a1).data["code"]
        Booking.objects.filter(code=code).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        with patch("apps.bookings.realtime.broadcast_seats") as broadcast:
            with self.captureOnCommitCallbacks(execute=True):
                services.expire_pending_bookings()
        broadcast.assert_called_once_with(
            self.showtime.id, "seats_released", [self.a1.id]
        )


@override_settings(REDIS_URL=TEST_REDIS_URL, CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
class ConcurrentHoldTests(TransactionTestCase):
    """TransactionTestCase để các thread thấy dữ liệu đã commit của nhau."""

    def setUp(self):
        get_redis().flushdb()
        self.showtime = build_showtime()
        self.seat = seat(self.showtime, "A", 1)
        self.users = [
            User.objects.create(username=f"u{i}", email=f"u{i}@example.com")
            for i in range(20)
        ]

    def tearDown(self):
        get_redis().flushdb()

    def test_only_one_user_wins_the_same_seat(self):
        url = reverse("showtime-hold", args=[self.showtime.id])

        def attempt(user):
            try:
                client = APIClient()
                client.force_authenticate(user)
                return client.post(
                    url, {"seat_ids": [self.seat.id]}, format="json"
                ).status_code
            finally:
                connection.close()  # mỗi thread có kết nối DB riêng, phải đóng

        with ThreadPoolExecutor(max_workers=20) as pool:
            codes = list(pool.map(attempt, self.users))

        self.assertEqual(codes.count(201), 1, codes)
        self.assertEqual(codes.count(409), 19, codes)
        self.assertEqual(
            BookingSeat.objects.filter(seat=self.seat, is_active=True).count(), 1
        )

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.cinemas.models import Cinema, Room
from apps.cinemas.services import generate_seats
from apps.movies.models import Movie
from apps.users.models import User

from .models import Showtime


class ShowtimeApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "admin1", "admin1@example.com", "Str0ng!Pass_123", role=User.Role.ADMIN
        )
        self.customer = User.objects.create_user("cus1", "cus1@example.com", "Str0ng!Pass_123")
        self.movie = Movie.objects.create(
            title="Phim A", duration_minutes=120, release_date="2026-10-01", status="now_showing"
        )
        cinema = Cinema.objects.create(name="C1", address="x", city="HCM")
        self.room = Room.objects.create(cinema=cinema, name="R1")
        self.room2 = Room.objects.create(cinema=cinema, name="R2")
        self.empty_room = Room.objects.create(cinema=cinema, name="R3")   # chưa có ghế
        for room in (self.room, self.room2):
            generate_seats(room, rows=2, seats_per_row=3)
        self.base = (timezone.now() + timedelta(days=2)).replace(minute=0, second=0, microsecond=0)

    def make(self, start, room=None, **kwargs):
        return Showtime.objects.create(
            movie=self.movie, room=room or self.room, start_time=start,
            price_standard=80000, price_vip=100000, price_couple=180000, **kwargs,
        )

    def payload(self, start, room=None):
        return {
            "movie": self.movie.id, "room": (room or self.room).id,
            "start_time": start.isoformat(),
            "price_standard": 80000, "price_vip": 100000, "price_couple": 180000,
        }

    def post(self, start, room=None):
        self.client.force_authenticate(self.admin)
        return self.client.post(reverse("showtime-list"), self.payload(start, room), format="json")

    def test_admin_creates_showtime_and_end_time_is_computed(self):
        res = self.post(self.base)
        self.assertEqual(res.status_code, 201)
        showtime = Showtime.objects.get(pk=res.data["id"])
        self.assertEqual(showtime.end_time, self.base + timedelta(minutes=120))

    def test_customer_cannot_create(self):
        self.client.force_authenticate(self.customer)
        res = self.client.post(reverse("showtime-list"), self.payload(self.base), format="json")
        self.assertEqual(res.status_code, 403)

    def test_overlap_is_rejected(self):
        self.make(self.base)
        self.assertEqual(self.post(self.base + timedelta(minutes=60)).status_code, 400)

    def test_cleaning_buffer_is_enforced(self):
        self.make(self.base)   # kết thúc lúc base + 120 phút
        self.assertEqual(self.post(self.base + timedelta(minutes=134)).status_code, 400)
        self.assertEqual(self.post(self.base + timedelta(minutes=135)).status_code, 201)

    def test_same_time_in_other_room_is_ok(self):
        self.make(self.base)
        self.assertEqual(self.post(self.base, room=self.room2).status_code, 201)

    def test_past_start_is_rejected(self):
        res = self.post(timezone.now() - timedelta(hours=1))
        self.assertEqual(res.status_code, 400)

    def test_room_without_seats_is_rejected(self):
        self.assertEqual(self.post(self.base, room=self.empty_room).status_code, 400)

    def test_db_constraint_blocks_overlap_even_without_serializer(self):
        self.make(self.base)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make(self.base + timedelta(minutes=30))

    def test_cancelled_showtime_frees_the_slot(self):
        showtime = self.make(self.base)
        showtime.is_active = False
        showtime.save()
        self.make(self.base)   # không được raise

    def test_filter_by_date_and_cinema(self):
        self.make(self.base)
        self.make(self.base + timedelta(days=3))
        local_date = timezone.localtime(self.base).date().isoformat()

        res = self.client.get(reverse("showtime-list"), {"date": local_date})
        self.assertEqual(res.data["count"], 1)
        res = self.client.get(reverse("showtime-list"), {"cinema": 9999})
        self.assertEqual(res.data["count"], 0)

    def test_public_hides_past_and_cancelled(self):
        self.make(self.base, is_active=False)
        self.make(timezone.now() - timedelta(days=1))
        self.make(self.base + timedelta(days=1))
        res = self.client.get(reverse("showtime-list"))
        self.assertEqual(res.data["count"], 1)

    def test_list_has_no_n_plus_one(self):
        for i in range(3):
            self.make(self.base + timedelta(hours=4 * i))
        with self.assertNumQueries(2):   # count + select (đã select_related)
            self.client.get(reverse("showtime-list"))

    def test_seats_endpoint_includes_price(self):
        showtime = self.make(self.base)
        res = self.client.get(reverse("showtime-seats", args=[showtime.id]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 6)
        self.assertEqual(res.data[0]["price"], 80000)
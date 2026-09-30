from django.urls import reverse
from rest_framework.test import APITestCase

from apps.users.models import User

from .models import Cinema, Room, Seat


class CinemaApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "admin1", "admin1@example.com", "Str0ng!Pass_123", role=User.Role.ADMIN
        )
        self.customer = User.objects.create_user(
            "cus1", "cus1@example.com", "Str0ng!Pass_123"
        )
        self.cinema = Cinema.objects.create(name="CGV Test", address="1 Test", city="HCM")
        self.room = Room.objects.create(cinema=self.cinema, name="Room 1")

    def test_generate_seats_as_admin(self):
        self.client.force_authenticate(self.admin)
        url = reverse("room-generate-seats", args=[self.room.id])
        payload = {"rows": 3, "seats_per_row": 4, "vip_rows": ["c"]}

        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Seat.objects.filter(room=self.room).count(), 12)
        self.assertEqual(
            Seat.objects.filter(room=self.room, seat_type="vip").count(), 4
        )

        # Gọi lần 2 phải bị từ chối
        self.assertEqual(self.client.post(url, payload, format="json").status_code, 409)

    def test_generate_seats_rejects_invalid_row(self):
        self.client.force_authenticate(self.admin)
        url = reverse("room-generate-seats", args=[self.room.id])
        res = self.client.post(url, {"rows": 2, "seats_per_row": 4, "vip_rows": ["Z"]}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_customer_cannot_generate_seats(self):
        self.client.force_authenticate(self.customer)
        url = reverse("room-generate-seats", args=[self.room.id])
        res = self.client.post(url, {"rows": 2, "seats_per_row": 4}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_inactive_cinema_hidden_from_public(self):
        Cinema.objects.create(name="Closed", address="x", city="HCM", is_active=False)
        res = self.client.get(reverse("cinema-list"))
        self.assertEqual(res.data["count"], 1)

    def test_delete_not_allowed(self):
        self.client.force_authenticate(self.admin)
        res = self.client.delete(reverse("cinema-detail", args=[self.cinema.id]))
        self.assertEqual(res.status_code, 405)
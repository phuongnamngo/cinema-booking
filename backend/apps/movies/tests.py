from django.urls import reverse
from rest_framework.test import APITestCase

from apps.users.models import User

from .models import Genre, Movie


class MovieApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "admin1", "admin1@example.com", "Str0ng!Pass_123", role=User.Role.ADMIN
        )
        self.customer = User.objects.create_user(
            "cus1", "cus1@example.com", "Str0ng!Pass_123"
        )
        self.genre = Genre.objects.create(name="Action")
        self.payload = {
            "title": "Test Movie",
            "duration_minutes": 120,
            "release_date": "2026-10-01",
            "age_rating": "T13",
            "status": "now_showing",
            "genre_ids": [self.genre.id],
        }

    def test_anonymous_can_list(self):
        self.assertEqual(self.client.get(reverse("movie-list")).status_code, 200)

    def test_anonymous_cannot_create(self):
        res = self.client.post(reverse("movie-list"), self.payload, format="json")
        self.assertEqual(res.status_code, 401)

    def test_customer_cannot_create(self):
        self.client.force_authenticate(self.customer)
        res = self.client.post(reverse("movie-list"), self.payload, format="json")
        self.assertEqual(res.status_code, 403)

    def test_admin_can_create_with_genres(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(reverse("movie-list"), self.payload, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["genres"][0]["name"], "Action")

    def test_filter_by_status(self):
        for i, st in enumerate(["now_showing", "coming_soon", "now_showing"]):
            Movie.objects.create(
                title=f"M{i}", duration_minutes=90, release_date="2026-10-01", status=st
            )
        res = self.client.get(reverse("movie-list"), {"status": "now_showing"})
        self.assertEqual(res.data["count"], 2)

    def test_list_has_no_n_plus_one(self):
        for i in range(5):
            m = Movie.objects.create(title=f"M{i}", duration_minutes=90, release_date="2026-10-01")
            m.genres.add(self.genre)
        # count + movies + prefetch genres = 3 query, bất kể có bao nhiêu phim
        with self.assertNumQueries(3):
            self.client.get(reverse("movie-list"))
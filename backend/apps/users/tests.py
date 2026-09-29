from django.urls import reverse
from rest_framework.test import APITestCase

from .models import User


class AuthTests(APITestCase):
    payload = {
        "username": "alice",
        "email": "Alice@Example.com",
        "password": "Str0ng!Pass_123",
        "password_confirm": "Str0ng!Pass_123",
    }

    def test_register_ignores_role(self):
        res = self.client.post(reverse("register"), {**self.payload, "role": "admin"})
        self.assertEqual(res.status_code, 201)
        user = User.objects.get(username="alice")
        self.assertEqual(user.role, User.Role.CUSTOMER)   # role bị bỏ qua
        self.assertEqual(user.email, "alice@example.com")  # email được chuẩn hóa

    def test_login_with_email_and_me(self):
        self.client.post(reverse("register"), self.payload)
        res = self.client.post(
            reverse("login"),
            {"username": "alice@example.com", "password": self.payload["password"]},
        )
        self.assertEqual(res.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        me = self.client.get(reverse("me"))
        self.assertEqual(me.data["username"], "alice")

    def test_me_requires_auth(self):
        self.assertEqual(self.client.get(reverse("me")).status_code, 401)
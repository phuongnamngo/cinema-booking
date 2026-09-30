from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .tasks import flush_expired_tokens, send_welcome_email


class UserTaskTests(TestCase):
    def test_welcome_email_is_sent(self):
        user = User.objects.create_user("alice", "alice@example.com", "Str0ng!Pass_123")
        send_welcome_email(user.id)   # gọi thẳng hàm; test runner tự dùng email backend trong bộ nhớ
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["alice@example.com"])

    def test_welcome_email_ignores_deleted_user(self):
        send_welcome_email(999999)   # không được raise
        self.assertEqual(len(mail.outbox), 0)

    def test_flush_expired_tokens(self):
        user = User.objects.create_user("bob", "bob@example.com", "Str0ng!Pass_123")
        RefreshToken.for_user(user)
        OutstandingToken.objects.update(expires_at=timezone.now() - timedelta(days=1))
        flush_expired_tokens()
        self.assertEqual(OutstandingToken.objects.count(), 0)


class RegisterEnqueuesEmailTests(APITestCase):
    payload = {
        "username": "carol",
        "email": "carol@example.com",
        "password": "Str0ng!Pass_123",
        "password_confirm": "Str0ng!Pass_123",
    }

    def test_register_enqueues_welcome_email_after_commit(self):
        with patch("apps.users.views.send_welcome_email.delay") as delay:
            with self.captureOnCommitCallbacks(execute=True):
                res = self.client.post(reverse("register"), self.payload)
        self.assertEqual(res.status_code, 201)
        delay.assert_called_once_with(res.data["id"])
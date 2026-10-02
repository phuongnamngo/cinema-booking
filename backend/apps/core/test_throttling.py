from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.settings import api_settings
from rest_framework.test import APITestCase

from apps.bookings.staff_views import CheckInView
from apps.bookings.views import BookingViewSet, HoldSeatsView
from apps.payments.views import CreatePaymentView
from apps.users.models import User
from apps.users.views import LoginView, RegisterView

from .testing import BrokenCache, rates
from rest_framework.throttling import SimpleRateThrottle

PASSWORD = "Str0ng!Pass_123"


class ScopeConfigTests(SimpleTestCase):
    def test_every_scope_used_by_a_view_has_a_configured_rate(self):
        used = [
            LoginView.throttle_scope, RegisterView.throttle_scope, HoldSeatsView.throttle_scope,
            CreatePaymentView.throttle_scope, CheckInView.throttle_scope,
            BookingViewSet.voucher.kwargs["throttle_scope"],
        ]
        configured = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        for scope in used:
            self.assertIn(scope, configured)   # gõ sai tên scope sẽ báo ở đây, thay vì lỗi 500 lúc chạy


class ThrottleTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def bad_login(self, **extra):
        return self.client.post(
            reverse("login"), {"username": "alice", "password": "wrong"}, format="json", **extra
        )


class LoginThrottleTests(ThrottleTestCase):
    def test_blocks_after_the_limit_even_with_the_right_password(self):
        User.objects.create_user("alice", "alice@example.com", PASSWORD)
        with rates(login="3/min"):
            self.assertEqual([self.bad_login().status_code for _ in range(3)], [401, 401, 401])
            res = self.client.post(
                reverse("login"), {"username": "alice", "password": PASSWORD}, format="json"
            )
        self.assertEqual(res.status_code, 429)
        self.assertGreater(int(res["Retry-After"]), 0)
        self.assertIn("quá nhanh", res.data["detail"])
        self.assertRegex(res.data["detail"], r"\d+ giây")

    def test_the_limit_is_per_ip(self):
        with rates(login="2/min"):
            for _ in range(2):
                self.bad_login(REMOTE_ADDR="10.0.0.1")
            self.assertEqual(self.bad_login(REMOTE_ADDR="10.0.0.1").status_code, 429)
            self.assertEqual(self.bad_login(REMOTE_ADDR="10.0.0.2").status_code, 401)

    def test_spoofed_forwarded_for_header_is_ignored_when_there_is_no_proxy(self):
        with rates(login="3/min"):
            codes = [self.bad_login(HTTP_X_FORWARDED_FOR=f"6.6.6.{i}").status_code for i in range(4)]
        self.assertEqual(codes, [401, 401, 401, 429])   # đổi header mỗi lần cũng vô ích

    def test_behind_one_trusted_proxy_the_client_is_the_last_hop(self):
        with rates(login="3/min"), patch_proxies(1):
            # Kẻ tấn công nhét địa chỉ giả ở đầu, nhưng Nginx luôn nối địa chỉ thật vào CUỐI
            codes = [
                self.bad_login(HTTP_X_FORWARDED_FOR=f"6.6.6.{i}, 203.0.113.7").status_code
                for i in range(4)
            ]
            other_client = self.bad_login(HTTP_X_FORWARDED_FOR="6.6.6.9, 198.51.100.1")
        self.assertEqual(codes, [401, 401, 401, 429])
        self.assertEqual(other_client.status_code, 401)


def patch_proxies(count):
    from unittest.mock import patch

    return patch.object(api_settings, "NUM_PROXIES", count)


class OtherThrottleTests(ThrottleTestCase):
    def test_register_is_limited(self):
        def register(i):
            return self.client.post(reverse("register"), {
                "username": f"user{i}", "email": f"user{i}@example.com",
                "password": PASSWORD, "password_confirm": PASSWORD,
            }, format="json").status_code

        with rates(register="2/hour"):
            self.assertEqual([register(i) for i in range(3)], [201, 201, 429])

    def test_anonymous_and_authenticated_requests_use_separate_buckets(self):
        user = User.objects.create_user("alice", "alice@example.com", PASSWORD)
        with rates(anon="2/min"):
            codes = [self.client.get(reverse("movie-list")).status_code for _ in range(3)]
            self.client.force_authenticate(user)   # khách hết lượt không kéo theo người đã đăng nhập
            logged_in = self.client.get(reverse("movie-list")).status_code
        self.assertEqual(codes, [200, 200, 429])
        self.assertEqual(logged_in, 200)

    def test_the_payment_webhook_is_never_throttled(self):
        with rates(anon="1/min"):
            codes = [
                self.client.post(
                    reverse("payment-webhook-mock"), data=b"{}", content_type="application/json"
                ).status_code
                for _ in range(3)
            ]
        self.assertEqual(codes, [401, 401, 401])   # sai chữ ký, chứ không phải 429

    def test_a_broken_cache_fails_open(self):
        with SimpleRateThrottle_cache(BrokenCache()), self.assertLogs("apps.core.throttling", "WARNING"):
            res = self.client.get(reverse("movie-list"))
        self.assertEqual(res.status_code, 200)   # Redis sập không được kéo cả API sập theo


def SimpleRateThrottle_cache(replacement):
    from unittest.mock import patch

    return patch.object(SimpleRateThrottle, "cache", replacement)
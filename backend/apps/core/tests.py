import json
import logging
from unittest.mock import patch

from django.db import OperationalError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.bookings.tests import TEST_REDIS_URL
from apps.users.models import User

from .logs import JsonFormatter, RequestIdFilter, request_id_var
from .sentry import build_scrubber


class RequestContextTests(TestCase):
    def test_generates_a_request_id_and_returns_it(self):
        res = self.client.get("/healthz")
        self.assertRegex(res["X-Request-ID"], r"^[0-9a-f]{32}$")

    def test_reuses_a_well_formed_incoming_id(self):
        res = self.client.get("/healthz", HTTP_X_REQUEST_ID="abc-123_DEF.456")
        self.assertEqual(res["X-Request-ID"], "abc-123_DEF.456")

    def test_replaces_malformed_or_malicious_ids(self):
        bad_ids = [
            "short",
            "has space in it",
            "x" * 65,
            "line\nbreak-injection",
            "<script>alert(1)</script>",
            "valid-id-123\n",   # "$" của regex khớp trước dấu xuống dòng cuối: match() sẽ để lọt cái này
        ]
        for bad in bad_ids:
            with self.subTest(bad=bad):
                res = self.client.get("/healthz", HTTP_X_REQUEST_ID=bad)
                self.assertRegex(res["X-Request-ID"], r"^[0-9a-f]{32}$")

    def test_access_log_has_method_path_status_and_never_the_query_string(self):
        with self.assertLogs("apps.core.access", level="INFO") as logs:
            self.client.get(reverse("genre-list"), {"token": "SECRET"})
        record = logs.records[0]
        self.assertEqual((record.method, record.path, record.status), ("GET", "/api/v1/genres/", 200))
        self.assertIsNone(record.user_id)
        self.assertNotIn("SECRET", logs.output[0] + str(record.__dict__))

    def test_access_log_records_the_authenticated_user(self):
        user = User.objects.create_user("alice", "alice@example.com", "Str0ng!Pass_123")
        client = APIClient()
        client.force_authenticate(user)
        with self.assertLogs("apps.core.access", level="INFO") as logs:
            client.get(reverse("genre-list"))
        self.assertEqual(logs.records[0].user_id, user.pk)

    def test_health_probes_are_not_access_logged_at_info_level(self):
        with self.assertNoLogs("apps.core.access", level="INFO"):
            self.client.get("/healthz")


class LoggingTests(SimpleTestCase):
    @staticmethod
    def record(message="hello %s", args=("world",), exc_info=None):
        return logging.LogRecord("apps.x", logging.INFO, __file__, 1, message, args, exc_info)

    def test_json_formatter_emits_one_valid_json_line_with_extras(self):
        record = self.record()
        record.status = 200
        line = JsonFormatter().format(record)
        data = json.loads(line)
        self.assertEqual((data["message"], data["level"], data["status"]), ("hello world", "INFO", 200))
        self.assertEqual(data["request_id"], "-")
        self.assertTrue(data["time"].endswith("Z"))   # luôn UTC

    def test_newlines_in_a_message_cannot_forge_a_second_log_line(self):
        line = JsonFormatter().format(self.record("a\nFAKE LINE", ()))
        self.assertNotIn("\n", line)
        self.assertEqual(json.loads(line)["message"], "a\nFAKE LINE")

    def test_exception_is_included(self):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            data = json.loads(JsonFormatter().format(self.record(exc_info=sys.exc_info())))
        self.assertIn("ValueError: boom", data["exception"])

    def test_filter_attaches_the_current_request_id(self):
        token = request_id_var.set("req-12345678")
        try:
            record = self.record()
            RequestIdFilter().filter(record)
        finally:
            request_id_var.reset(token)
        self.assertEqual(record.request_id, "req-12345678")


@override_settings(REDIS_URL=TEST_REDIS_URL)
class HealthTests(TestCase):
    def test_liveness(self):
        res = self.client.get("/healthz")
        self.assertEqual((res.status_code, res.json()), (200, {"status": "ok"}))

    def test_readiness_when_everything_is_up(self):
        res = self.client.get("/readyz")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok", "database": "ok", "redis": "ok"})
        self.assertIn("no-store", res["Cache-Control"])

    def test_readiness_fails_when_redis_is_down(self):
        with override_settings(REDIS_URL="redis://127.0.0.1:1/0"), \
                self.assertLogs("apps.core.health", "ERROR"):
            res = self.client.get("/readyz")
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.json(), {"status": "fail", "database": "ok", "redis": "fail"})

    def test_readiness_fails_when_database_is_down_without_leaking_details(self):
        boom = OperationalError("password=hunter2 host=10.0.0.5")
        with patch("apps.core.health.check_database", side_effect=boom), \
                self.assertLogs("apps.core.health", "ERROR"):
            res = self.client.get("/readyz")
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.json()["database"], "fail")
        self.assertNotIn("hunter2", res.content.decode())   # chi tiết lỗi chỉ vào log, không ra response

    def test_probes_only_accept_safe_methods(self):
        self.assertEqual(self.client.post("/healthz").status_code, 405)


class SentryScrubberTests(SimpleTestCase):
    def test_project_specific_secrets_are_filtered_and_the_rest_is_kept(self):
        event = {"request": {
            "data": {"refresh": "abc", "password": "p@ss", "username": "alice"},
            "headers": {"X-Signature": "deadbeef", "User-Agent": "curl"},
        }}
        build_scrubber().scrub_event(event)

        def shown(value):   # giá trị bị lọc là AnnotatedValue("[Filtered]")
            return getattr(value, "value", value)

        data, headers = event["request"]["data"], event["request"]["headers"]
        self.assertNotEqual(shown(data["refresh"]), "abc")
        self.assertNotEqual(shown(data["password"]), "p@ss")
        self.assertNotEqual(shown(headers["X-Signature"]), "deadbeef")
        self.assertEqual((data["username"], headers["User-Agent"]), ("alice", "curl"))
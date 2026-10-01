from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.db import IntegrityError, connection, transaction
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.cinemas.models import Cinema
from apps.showtimes.models import Showtime
from apps.users.models import User

from .models import Booking, BookingSeat
from .tests import build_showtime, seat

CHECKIN_SETTINGS = dict(CHECKIN_OPENS_BEFORE_MINUTES=60)
PASSWORD = "Str0ng!Pass_123"


class CheckinMixin:
    def setUp(self):
        self.customer = User.objects.create_user("cus1", "cus1@example.com", PASSWORD)
        self.showtime = build_showtime()
        self.cinema = self.showtime.room.cinema
        self.staff = User.objects.create_user(
            "staff1",
            "staff1@example.com",
            PASSWORD,
            role=User.Role.STAFF,
            cinema=self.cinema,
        )
        self.a1 = seat(self.showtime, "A", 1)
        self.set_start(
            timezone.now() + timedelta(minutes=30)
        )  # cửa sổ check-in đang mở

    def set_start(self, start):
        end = start + timedelta(minutes=self.showtime.movie.duration_minutes)
        Showtime.objects.filter(pk=self.showtime.pk).update(
            start_time=start, end_time=end
        )
        self.showtime.refresh_from_db()

    def ticket(self, status=Booking.Status.CONFIRMED):
        booking = Booking.objects.create(
            user=self.customer,
            showtime=self.showtime,
            status=status,
            total_amount=80000,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        BookingSeat.objects.create(
            booking=booking,
            showtime=self.showtime,
            seat=self.a1,
            price=80000,
            is_active=status in (Booking.Status.PENDING, Booking.Status.CONFIRMED),
        )
        return booking

    def checkin(self, code, user=None):
        self.client.force_authenticate(user or self.staff)
        return self.client.post(reverse("staff-checkin"), {"code": code}, format="json")


@override_settings(**CHECKIN_SETTINGS)
class CheckinPermissionTests(CheckinMixin, APITestCase):
    def test_anonymous_and_customer_are_rejected(self):
        booking = self.ticket()
        anonymous = self.client.post(
            reverse("staff-checkin"), {"code": booking.code}, format="json"
        )
        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(
            self.checkin(booking.code, user=self.customer).status_code, 403
        )

    def test_staff_without_cinema_is_rejected(self):
        booking = self.ticket()
        User.objects.filter(pk=self.staff.pk).update(cinema=None)
        self.staff.refresh_from_db()
        self.assertEqual(self.checkin(booking.code).status_code, 403)

    def test_staff_of_another_cinema_is_rejected(self):
        other = Cinema.objects.create(name="C2", address="y", city="HN")
        outsider = User.objects.create_user(
            "staff2", "staff2@example.com", PASSWORD, role=User.Role.STAFF, cinema=other
        )
        booking = self.ticket()
        self.assertEqual(self.checkin(booking.code, user=outsider).status_code, 403)
        booking.refresh_from_db()
        self.assertIsNone(booking.checked_in_at)

    def test_admin_can_check_in_at_any_cinema(self):
        admin = User.objects.create_user(
            "admin1", "admin1@example.com", PASSWORD, role=User.Role.ADMIN
        )
        booking = self.ticket()
        self.assertEqual(self.checkin(booking.code, user=admin).status_code, 200)

    def test_staff_cannot_reassign_own_cinema_or_role(self):
        other = Cinema.objects.create(name="C2", address="y", city="HN")
        self.client.force_authenticate(self.staff)
        res = self.client.patch(
            reverse("me"), {"cinema": other.id, "role": "admin"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.cinema_id, self.cinema.id)
        self.assertEqual(self.staff.role, User.Role.STAFF)


@override_settings(**CHECKIN_SETTINGS)
class CheckinFlowTests(CheckinMixin, APITestCase):
    def test_success_marks_ticket_and_returns_details(self):
        booking = self.ticket()
        res = self.checkin(booking.code)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["checked_in_by"], "staff1")
        self.assertEqual(res.data["seats"][0]["label"], "A1")
        booking.refresh_from_db()
        self.assertIsNotNone(booking.checked_in_at)
        self.assertEqual(booking.checked_in_by_id, self.staff.id)

    def test_code_is_normalised(self):
        booking = self.ticket()
        self.assertEqual(self.checkin(f"  {booking.code.lower()} ").status_code, 200)

    def test_scanning_twice_is_a_conflict_not_a_second_success(self):
        booking = self.ticket()
        self.assertEqual(self.checkin(booking.code).status_code, 200)
        first = Booking.objects.get(pk=booking.pk).checked_in_at

        res = self.checkin(booking.code)
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data["reason"], "already_checked_in")
        self.assertEqual(res.data["checked_in_by"], "staff1")
        self.assertIn("checked_in_at", res.data)
        self.assertEqual(
            Booking.objects.get(pk=booking.pk).checked_in_at, first
        )  # không bị ghi đè

    def test_rejects_unpaid_ticket(self):
        for status in (
            Booking.Status.PENDING,
            Booking.Status.EXPIRED,
            Booking.Status.CANCELLED,
        ):
            with self.subTest(status=status):
                booking = self.ticket(status=status)
                res = self.checkin(booking.code)
                self.assertEqual(
                    (res.status_code, res.data["reason"]), (409, "not_confirmed")
                )

    def test_time_window(self):
        booking = self.ticket()

        self.set_start(timezone.now() + timedelta(hours=2))  # cửa mở sau 1 giờ nữa
        self.assertEqual(self.checkin(booking.code).data["reason"], "too_early")

        self.set_start(
            timezone.now() - timedelta(hours=4)
        )  # phim 120 phút: đã hết từ 2 giờ trước
        self.assertEqual(self.checkin(booking.code).data["reason"], "too_late")

        self.set_start(
            timezone.now() - timedelta(minutes=30)
        )  # phim đang chiếu dở vẫn vào được
        self.assertEqual(self.checkin(booking.code).status_code, 200)

    def test_rejects_cancelled_showtime(self):
        booking = self.ticket()
        Showtime.objects.filter(pk=self.showtime.pk).update(is_active=False)
        self.assertEqual(
            self.checkin(booking.code).data["reason"], "showtime_cancelled"
        )

    def test_unknown_code_and_bad_body(self):
        self.assertEqual(self.checkin("ZZZZZZZZ").status_code, 404)
        self.client.force_authenticate(self.staff)
        res = self.client.post(reverse("staff-checkin"), {}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_db_refuses_checkin_of_unpaid_booking(self):
        booking = self.ticket(status=Booking.Status.PENDING)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Booking.objects.filter(pk=booking.pk).update(checked_in_at=timezone.now())


@override_settings(**CHECKIN_SETTINGS)
class TicketLookupTests(CheckinMixin, APITestCase):
    def test_lookup_reports_state_without_changing_it(self):
        booking = self.ticket()
        url = reverse("staff-ticket", kwargs={"code": booking.code})

        self.client.force_authenticate(self.staff)
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["can_check_in"])
        self.assertEqual(res.data["ticket"]["code"], booking.code)
        booking.refresh_from_db()
        self.assertIsNone(booking.checked_in_at)  # tra cứu không làm thay đổi gì

        self.checkin(booking.code)
        res = self.client.get(url)
        self.assertFalse(res.data["can_check_in"])
        self.assertEqual(res.data["reason"], "already_checked_in")

    def test_lookup_respects_roles_and_cinema_scope(self):
        booking = self.ticket()
        url = reverse("staff-ticket", kwargs={"code": booking.code})

        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get(url).status_code, 403)

        other = Cinema.objects.create(name="C2", address="y", city="HN")
        outsider = User.objects.create_user(
            "staff2", "staff2@example.com", PASSWORD, role=User.Role.STAFF, cinema=other
        )
        self.client.force_authenticate(outsider)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_authenticate(self.staff)
        self.assertEqual(
            self.client.get(
                reverse("staff-ticket", kwargs={"code": "ZZZZZZZZ"})
            ).status_code,
            404,
        )


@override_settings(**CHECKIN_SETTINGS)
class ConcurrentCheckinTests(CheckinMixin, TransactionTestCase):
    """TransactionTestCase để các thread thấy dữ liệu đã commit của nhau."""

    def test_parallel_scans_check_in_exactly_once(self):
        booking = self.ticket()
        scanners = [
            User.objects.create_user(
                f"s{i}",
                f"s{i}@example.com",
                PASSWORD,
                role=User.Role.STAFF,
                cinema=self.cinema,
            )
            for i in range(8)
        ]
        url = reverse("staff-checkin")

        def scan(user):
            try:
                client = APIClient()
                client.force_authenticate(user)
                return client.post(
                    url, {"code": booking.code}, format="json"
                ).status_code
            finally:
                connection.close()  # mỗi thread có kết nối DB riêng

        with ThreadPoolExecutor(max_workers=8) as pool:
            codes = list(pool.map(scan, scanners))

        self.assertEqual(sorted(codes), [200] + [409] * 7)
        booking.refresh_from_db()
        self.assertIsNotNone(booking.checked_in_at)

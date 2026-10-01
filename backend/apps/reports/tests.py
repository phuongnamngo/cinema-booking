from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.bookings.models import Booking, BookingSeat
from apps.bookings.tests import build_showtime
from apps.cinemas.models import Room, Seat
from apps.cinemas.services import generate_seats
from apps.movies.models import Movie
from apps.payments.models import Payment
from apps.showtimes.models import Showtime
from apps.users.models import User

VN = ZoneInfo("Asia/Ho_Chi_Minh")
PASSWORD = "Str0ng!Pass_123"
PENDING, FAILED = Booking.Status.PENDING, Payment.Status.FAILED


class ReportBase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin1", "admin1@example.com", PASSWORD, role=User.Role.ADMIN)
        self.staff = User.objects.create_user("staff1", "staff1@example.com", PASSWORD, role=User.Role.STAFF)
        self.customer = User.objects.create_user("cus1", "cus1@example.com", PASSWORD)
        self.client.force_authenticate(self.admin)

        self.showtime = build_showtime()
        # Thứ tự: A1-A3 (thường, 80.000), B1-B3 (VIP, 100.000)
        self.seats = list(Seat.objects.filter(room=self.showtime.room))
        self.day = timezone.localdate(self.showtime.start_time)

    def sell(self, showtime, seats, *, paid_at=None, booking_status=Booking.Status.CONFIRMED,
             pay_status=Payment.Status.SUCCEEDED):
        prices = [showtime.price_for(s.seat_type) for s in seats]
        booking = Booking.objects.create(
            user=self.customer, showtime=showtime, status=booking_status, total_amount=sum(prices),
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        BookingSeat.objects.bulk_create([
            BookingSeat(booking=booking, showtime=showtime, seat=s, price=p)
            for s, p in zip(seats, prices)
        ])
        Payment.objects.create(booking=booking, amount=sum(prices), status=pay_status, paid_at=paid_at)
        return booking

    def second_showtime(self):
        movie = Movie.objects.create(
            title="Phim B", duration_minutes=100, release_date="2026-10-01", status="now_showing"
        )
        room = Room.objects.create(cinema=self.showtime.room.cinema, name="R2")
        generate_seats(room, rows=1, seats_per_row=2)
        showtime = Showtime.objects.create(
            movie=movie, room=room, start_time=self.showtime.start_time,
            price_standard=90000, price_vip=110000, price_couple=190000,
        )
        return showtime, list(Seat.objects.filter(room=room))

    def get(self, name, **params):
        return self.client.get(reverse(name), params)

    def day_params(self):
        return {"date_from": self.day.isoformat(), "date_to": self.day.isoformat()}


class AccessAndValidationTests(ReportBase):
    def test_only_admin_can_read_reports(self):
        for name in ("report-revenue", "report-top-movies", "report-occupancy"):
            with self.subTest(name=name):
                self.client.force_authenticate(None)
                self.assertEqual(self.get(name).status_code, 401)
                for user in (self.customer, self.staff):
                    self.client.force_authenticate(user)
                    self.assertEqual(self.get(name).status_code, 403)
                self.client.force_authenticate(self.admin)
                self.assertEqual(self.get(name).status_code, 200)

    def test_parameter_validation(self):
        bad = [
            ("report-revenue", dict(date_from="2026-09-10", date_to="2026-09-01")),   # đảo ngược
            ("report-revenue", dict(date_from="2026-01-01", date_to="2026-09-30")),   # quá 92 ngày
            ("report-revenue", dict(date_from="khong-phai-ngay")),
            ("report-occupancy", dict(date_from="2026-08-01", date_to="2026-09-30")),   # quá 31 ngày
            ("report-top-movies", dict(limit=0)),
        ]
        for name, params in bad:
            with self.subTest(name=name, params=params):
                self.assertEqual(self.get(name, **params).status_code, 400)

    def test_default_range_is_last_seven_days(self):
        res = self.get("report-revenue")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["days"]), 7)
        self.assertEqual(res.data["days"][-1]["date"], timezone.localdate().isoformat())


class RevenueReportTests(ReportBase):
    def test_zero_fill_vietnam_dates_and_succeeded_only(self):
        s, seats = self.showtime, self.seats
        self.sell(s, [seats[0]], paid_at=datetime(2026, 9, 10, 23, 30, tzinfo=VN))   # 16:30 UTC ngày 10
        self.sell(s, [seats[1]], paid_at=datetime(2026, 9, 11, 0, 30, tzinfo=VN))    # 17:30 UTC ngày 10!
        self.sell(s, seats[2:4], paid_at=datetime(2026, 9, 13, 9, 0, tzinfo=VN))     # A3 + B1 = 180.000
        # Không được tính: thất bại và cần xử lý thủ công
        self.sell(s, [seats[4]], paid_at=datetime(2026, 9, 12, 9, 0, tzinfo=VN), pay_status=FAILED)
        self.sell(s, [seats[5]], paid_at=datetime(2026, 9, 12, 9, 0, tzinfo=VN),
                  pay_status=Payment.Status.NEEDS_REVIEW)

        res = self.get("report-revenue", date_from="2026-09-10", date_to="2026-09-13")
        rows = [(d["date"], d["revenue"], d["orders"]) for d in res.data["days"]]
        self.assertEqual(rows, [
            ("2026-09-10", 80000, 1),    # tách đúng ngày theo giờ Việt Nam
            ("2026-09-11", 80000, 1),    # (nếu nhóm theo UTC, hai giao dịch đầu sẽ nằm chung một ngày)
            ("2026-09-12", 0, 0),        # ngày không có giao dịch vẫn xuất hiện
            ("2026-09-13", 180000, 1),
        ])
        self.assertEqual(res.data["total_revenue"], 340000)
        self.assertEqual(res.data["total_orders"], 3)

    def test_payment_outside_range_is_excluded(self):
        self.sell(self.showtime, [self.seats[0]], paid_at=datetime(2026, 9, 9, 23, 59, tzinfo=VN))
        res = self.get("report-revenue", date_from="2026-09-10", date_to="2026-09-10")
        self.assertEqual(res.data["total_revenue"], 0)


class SalesReportTests(ReportBase):
    def test_top_movies_counts_only_confirmed_and_orders_by_tickets(self):
        other, other_seats = self.second_showtime()
        self.sell(self.showtime, self.seats[0:2])    # A1, A2: 160.000
        self.sell(self.showtime, self.seats[3:4])    # B1: 100.000
        self.sell(other, other_seats[0:1])           # 90.000
        self.sell(self.showtime, self.seats[4:5], booking_status=PENDING,
                  pay_status=Payment.Status.PENDING)   # đang giữ chỗ: không tính

        res = self.get("report-top-movies", **self.day_params())
        rows = [(m["title"], m["tickets"], m["revenue"]) for m in res.data["movies"]]
        self.assertEqual(rows, [("Phim A", 3, 260000), ("Phim B", 1, 90000)])

        limited = self.get("report-top-movies", limit=1, **self.day_params())
        self.assertEqual(len(limited.data["movies"]), 1)

    def test_occupancy_values_and_single_query(self):
        other, other_seats = self.second_showtime()
        self.sell(self.showtime, self.seats[0:3])    # 3/6
        self.sell(self.showtime, self.seats[3:4], booking_status=PENDING,
                  pay_status=Payment.Status.PENDING)   # giữ chỗ chưa trả tiền: chưa tính
        self.sell(other, other_seats)                # 2/2

        with self.assertNumQueries(1):   # JOIN + Subquery: số query không tăng theo số suất chiếu
            res = self.get("report-occupancy", **self.day_params())

        rows = {r["showtime_id"]: r for r in res.data["showtimes"]}
        mine = rows[self.showtime.id]
        self.assertEqual((mine["seats_total"], mine["seats_sold"]), (6, 3))
        self.assertAlmostEqual(mine["occupancy"], 0.5)
        self.assertAlmostEqual(rows[other.id]["occupancy"], 1.0)
        self.assertAlmostEqual(res.data["overall_occupancy"], 5 / 8, places=3)
        self.assertTrue(mine["start_time"].endswith("+07:00"))
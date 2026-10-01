import random
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.bookings.models import Booking, BookingSeat
from apps.cinemas.models import Room
from apps.movies.models import Movie
from apps.payments.models import Payment
from apps.showtimes.models import Showtime
from apps.showtimes.services import find_conflict
from apps.users.models import User

SLOTS = [(9, 30), (12, 30), (15, 30), (18, 30), (21, 30)]


class Command(BaseCommand):
    help = "Tạo nhân viên, khách hàng và lịch sử bán vé các ngày trước để thử báo cáo/check-in"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=14, help="Số ngày quá khứ (mặc định 14)")

    @transaction.atomic
    def handle(self, *args, **options):
        days = options["days"]
        rng = random.Random(42)   # cố định seed: chạy lại cho kết quả dễ so sánh
        now = timezone.now()
        today = timezone.localdate()

        rooms = list(
            Room.objects.filter(is_active=True, cinema__is_active=True, seats__isnull=False)
            .select_related("cinema")
            .distinct()
        )
        movies = list(Movie.objects.filter(status=Movie.Status.NOW_SHOWING))
        if not rooms or not movies:
            raise CommandError("Chưa có phim/phòng/ghế. Hãy chạy `seed_demo` trước.")

        # --- Tài khoản ---
        customers = []
        for i in range(1, 6):
            user, created = User.objects.get_or_create(
                username=f"customer{i}", defaults={"email": f"customer{i}@example.com"}
            )
            if created:
                user.set_password("Customer!Pass_123")
                user.save()
            customers.append(user)

        staff, created = User.objects.get_or_create(
            username="staff1",
            defaults={
                "email": "staff1@example.com",
                "role": User.Role.STAFF,
                "cinema": rooms[0].cinema,
            },
        )
        if created:
            staff.set_password("Staff!Pass_123")
            staff.save()

        # --- Suất chiếu trong quá khứ (tạo thẳng bằng ORM, bỏ qua kiểm tra "không xếp lịch quá khứ") ---
        created_showtimes = 0
        for back in range(1, days + 1):
            day = today - timedelta(days=back)
            bump = 20000 if day.weekday() >= 5 else 0
            for room in rooms:
                for hour, minute in SLOTS:
                    start = timezone.make_aware(datetime.combine(day, time(hour, minute)))
                    movie = rng.choice(movies)
                    end = start + timedelta(minutes=movie.duration_minutes)
                    if find_conflict(room, start, end):   # đã có suất: bỏ qua
                        continue
                    Showtime.objects.create(
                        movie=movie, room=room, start_time=start,
                        price_standard=80000 + bump,
                        price_vip=100000 + bump,
                        price_couple=180000 + bump,
                    )
                    created_showtimes += 1

        # --- Bán vé cho mọi suất đã qua mà chưa có đơn nào (nên chạy lại không bán trùng) ---
        window_start = timezone.make_aware(
            datetime.combine(today - timedelta(days=days), time.min)
        )
        unsold = Showtime.objects.filter(
            is_active=True,
            start_time__gte=window_start,
            start_time__lt=now,
            bookings__isnull=True,
        ).select_related("room")

        orders = tickets = 0
        for showtime in unsold:
            seats = list(showtime.room.seats.all())
            rng.shuffle(seats)
            sold = seats[: int(len(seats) * rng.uniform(0.15, 0.85))]

            i = 0
            while i < len(sold):
                group = sold[i : i + rng.randint(1, 4)]
                i += len(group)
                prices = [showtime.price_for(s.seat_type) for s in group]
                total = sum(prices)
                paid_at = showtime.start_time - timedelta(minutes=rng.randint(10, 60 * 24 * 3))
                used = rng.random() < 0.8   # 80% khách đã vào rạp

                booking = Booking.objects.create(
                    user=rng.choice(customers),
                    showtime=showtime,
                    status=Booking.Status.CONFIRMED,
                    total_amount=total,
                    expires_at=paid_at + timedelta(minutes=10),
                    checked_in_at=showtime.start_time - timedelta(minutes=rng.randint(5, 30)) if used else None,
                    checked_in_by=staff if used else None,
                )
                BookingSeat.objects.bulk_create([
                    BookingSeat(booking=booking, showtime=showtime, seat=s, price=p)
                    for s, p in zip(group, prices)
                ])
                Payment.objects.create(
                    booking=booking,
                    provider=Payment.Provider.MOCK,
                    amount=total,
                    status=Payment.Status.SUCCEEDED,
                    gateway_txn_id=f"SEED{booking.id:08d}",
                    paid_at=paid_at,
                )
                orders += 1
                tickets += len(group)

        self.stdout.write(self.style.SUCCESS(
            f"Xong. Suất chiếu mới: {created_showtimes}, đơn: {orders}, vé: {tickets}."
        ))
        self.stdout.write("Tài khoản: staff1@example.com / Staff!Pass_123, "
                          "customer1@example.com / Customer!Pass_123")
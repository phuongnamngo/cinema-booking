from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.cinemas.models import Cinema, Room
from apps.cinemas.services import generate_seats
from apps.movies.models import Genre, Movie
from apps.showtimes.models import Showtime
from apps.showtimes.services import find_conflict

NOW, SOON = Movie.Status.NOW_SHOWING, Movie.Status.COMING_SOON

GENRES = ["Hành động", "Hài", "Kinh dị", "Tình cảm", "Khoa học viễn tưởng", "Hoạt hình"]
MOVIES = [
    # (tiêu đề, phút, độ tuổi, trạng thái, thể loại)
    ("Hành Tinh Cuối Cùng", 138, "T13", NOW, ["Khoa học viễn tưởng", "Hành động"]),
    ("Đêm Sài Gòn", 112, "T16", NOW, ["Hành động"]),
    ("Ngày Mưa Ở Hà Nội", 105, "K", NOW, ["Tình cảm"]),
    ("Ma Xó", 98, "T18", NOW, ["Kinh dị"]),
    ("Biệt Đội Gấu Trúc", 95, "P", NOW, ["Hoạt hình", "Hài"]),
    ("Cưới Nhầm Chồng", 102, "T13", SOON, ["Hài", "Tình cảm"]),
]
CINEMAS = [
    ("Cinema Quận 1", "1 Lê Lợi, Quận 1", "Hồ Chí Minh"),
    ("Cinema Cầu Giấy", "1 Xuân Thủy, Cầu Giấy", "Hà Nội"),
]
SLOTS = [(9, 30), (12, 30), (15, 30), (18, 30), (21, 30)]


class Command(BaseCommand):
    help = "Tạo dữ liệu demo: thể loại, phim, rạp, phòng, ghế và suất chiếu 7 ngày tới"

    @transaction.atomic
    def handle(self, *args, **options):
        genres = {name: Genre.objects.get_or_create(name=name)[0] for name in GENRES}
        today = timezone.localdate()

        showing = []
        for title, minutes, rating, status, genre_names in MOVIES:
            release = today + timedelta(days=-14 if status == NOW else 14)
            movie, _ = Movie.objects.get_or_create(
                title=title,
                defaults={
                    "duration_minutes": minutes,
                    "age_rating": rating,
                    "status": status,
                    "release_date": release,
                    "synopsis": f"Nội dung demo của phim {title}.",
                },
            )
            movie.genres.set([genres[n] for n in genre_names])
            if movie.status == NOW:
                showing.append(movie)

        rooms = []
        for name, address, city in CINEMAS:
            cinema, _ = Cinema.objects.get_or_create(
                name=name, defaults={"address": address, "city": city}
            )
            for room_name in ("Phòng 1", "Phòng 2"):
                room, _ = Room.objects.get_or_create(cinema=cinema, name=room_name)
                if not room.seats.exists():
                    generate_seats(
                        room, rows=8, seats_per_row=12, vip_rows=["E", "F"], couple_rows=["H"]
                    )
                rooms.append(room)

        now, created = timezone.now(), 0
        for day_offset in range(7):
            day = today + timedelta(days=day_offset)
            bump = 20000 if day.weekday() >= 5 else 0      # cuối tuần đắt hơn
            for r, room in enumerate(rooms):
                for s, (hour, minute) in enumerate(SLOTS):
                    start = timezone.make_aware(datetime.combine(day, time(hour, minute)))
                    if start <= now:
                        continue
                    movie = showing[(day_offset + r * 2 + s) % len(showing)]
                    end = start + timedelta(minutes=movie.duration_minutes)
                    if find_conflict(room, start, end):     # chạy lại nhiều lần vẫn an toàn
                        continue
                    Showtime.objects.create(
                        movie=movie,
                        room=room,
                        start_time=start,
                        price_standard=80000 + bump,
                        price_vip=100000 + bump,
                        price_couple=180000 + bump,
                    )
                    created += 1

        self.stdout.write(self.style.SUCCESS(f"Xong. Đã tạo {created} suất chiếu mới."))
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
    # (tiêu đề, phút, độ tuổi, trạng thái, thể loại, file poster, tóm tắt)
    (
        "Hành Tinh Cuối Cùng", 138, "T13", NOW, ["Khoa học viễn tưởng", "Hành động"],
        "hanh-tinh-cuoi-cung.jpg",
        "Năm 2187, Trái Đất chỉ còn là ký ức. Phi hành gia Lâm Phong bị kẹt lại trên một hành tinh "
        "sa mạc đỏ, nơi mặt trời đang hấp hối và các mặt trăng vỡ vụn từng ngày. Anh có 72 giờ để "
        "kích hoạt cổng dịch chuyển cuối cùng, trước khi cả hành tinh bị nuốt chửng.",
    ),
    (
        "Đêm Sài Gòn", 112, "T16", NOW, ["Hành động"],
        "dem-sai-gon.jpg",
        "Cựu tay đua đường phố Tuấn buộc phải quay lại thế giới ngầm Sài Gòn để cứu em trai khỏi "
        "món nợ với một băng nhóm khét tiếng. Một đêm mưa, một chiếc xe máy và những con hẻm "
        "không lối thoát sẽ quyết định số phận của cả hai anh em.",
    ),
    (
        "Ngày Mưa Ở Hà Nội", 105, "K", NOW, ["Tình cảm"],
        "ngay-mua-o-ha-noi.jpg",
        "Một chiếc ô trong suốt bỏ quên ở phố cổ đưa Minh và An gặp nhau giữa mùa mưa Hà Nội. "
        "Mỗi cơn mưa là một lần hẹn, cho đến khi An phải chọn giữa giấc mơ du học và người "
        "con trai luôn chờ cô bên Hồ Gươm.",
    ),
    (
        "Ma Xó", 98, "T18", NOW, ["Kinh dị"],
        "ma-xo.jpg",
        "Về quê chịu tang bà nội, Hạnh phát hiện góc nhà cạnh bàn thờ luôn lạnh lẽo dù trời oi "
        "bức. Người làng thì thầm về \"ma xó\" giữ của trong dòng họ, và mỗi đêm ngọn đèn dầu lại "
        "tự tắt đúng lúc nửa đêm.",
    ),
    (
        "Biệt Đội Gấu Trúc", 95, "P", NOW, ["Hoạt hình", "Hài"],
        "biet-doi-gau-truc.jpg",
        "Năm chú gấu trúc vụng về tự phong mình là siêu anh hùng của rừng trúc. Khi kho măng "
        "của cả khu rừng bị đánh cắp, biệt đội mặc áo choàng tự may phải lên đường trong phi vụ "
        "giải cứu hài hước nhất mùa hè.",
    ),
    (
        "Cưới Nhầm Chồng", 102, "T13", SOON, ["Hài", "Tình cảm"],
        "cuoi-nham-chong.jpg",
        "Ngay trong ngày cưới, cô dâu Thảo phát hiện có tới hai chú rể cùng tên, cùng giờ đón dâu "
        "và cùng một tấm thiệp mời. Hai họ nhà trai, một cô dâu và hàng loạt hiểu lầm dở khóc "
        "dở cười bắt đầu.",
    ),
]
DEFAULT_ASSET_BASE = "http://localhost:5173"   # poster nằm trong frontend/public/posters
CINEMAS = [
    ("Cinema Quận 1", "1 Lê Lợi, Quận 1", "Hồ Chí Minh"),
    ("Cinema Cầu Giấy", "1 Xuân Thủy, Cầu Giấy", "Hà Nội"),
]
SLOTS = [(9, 30), (12, 30), (15, 30), (18, 30), (21, 30)]


class Command(BaseCommand):
    help = "Tạo dữ liệu demo: thể loại, phim, rạp, phòng, ghế và suất chiếu 7 ngày tới"

    def add_arguments(self, parser):
        parser.add_argument(
            "--asset-base",
            default=DEFAULT_ASSET_BASE,
            help=f"Origin phục vụ /posters/*.jpg (mặc định {DEFAULT_ASSET_BASE})",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        genres = {name: Genre.objects.get_or_create(name=name)[0] for name in GENRES}
        today = timezone.localdate()
        asset_base = options["asset_base"].rstrip("/")

        showing = []
        for title, minutes, rating, status, genre_names, poster, synopsis in MOVIES:
            release = today + timedelta(days=-14 if status == NOW else 14)
            movie, _ = Movie.objects.get_or_create(
                title=title,
                defaults={
                    "duration_minutes": minutes,
                    "age_rating": rating,
                    "status": status,
                    "release_date": release,
                },
            )
            # Chỉ điền chỗ còn trống/còn là nội dung demo cũ: không ghi đè dữ liệu đã sửa trong admin
            if not movie.poster_url:
                movie.poster_url = f"{asset_base}/posters/{poster}"
            if not movie.synopsis or movie.synopsis.startswith("Nội dung demo của phim"):
                movie.synopsis = synopsis
            movie.save(update_fields=["poster_url", "synopsis", "updated_at"])
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
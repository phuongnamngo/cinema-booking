from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.movies.models import Movie

from .models import Showtime

CLEANING_BUFFER = timedelta(minutes=15)


def find_conflict(room, start, end, exclude_id=None):
    """Tìm suất chiếu trong cùng phòng chồng lấn [start, end], tính cả thời gian dọn phòng."""
    qs = Showtime.objects.filter(
        room=room,
        is_active=True,
        start_time__lt=end + CLEANING_BUFFER,
        end_time__gt=start - CLEANING_BUFFER,
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs.select_related("movie").first()


def validate_schedule(*, movie, room, start_time, exclude_id=None, check_past=True):
    """Kiểm tra quy tắc xếp lịch. Trả về end_time nếu hợp lệ, ngược lại raise ValidationError."""
    if movie.status == Movie.Status.ENDED:
        raise ValidationError({"movie": "Phim đã ngừng chiếu."})
    if not (room.is_active and room.cinema.is_active):
        raise ValidationError({"room": "Phòng hoặc rạp đang ngừng hoạt động."})
    if not room.seats.exists():
        raise ValidationError({"room": "Phòng chưa có sơ đồ ghế."})
    if check_past and start_time <= timezone.now():
        raise ValidationError({"start_time": "Không thể xếp suất chiếu trong quá khứ."})

    end_time = start_time + timedelta(minutes=movie.duration_minutes)
    conflict = find_conflict(room, start_time, end_time, exclude_id)
    if conflict:
        local = timezone.localtime
        raise ValidationError({
            "start_time": (
                f"Trùng lịch với '{conflict.movie.title}' "
                f"({local(conflict.start_time):%H:%M}-{local(conflict.end_time):%H:%M}, "
                f"cần cách nhau tối thiểu {int(CLEANING_BUFFER.total_seconds() // 60)} phút để dọn phòng)."
            )
        })
    return end_time
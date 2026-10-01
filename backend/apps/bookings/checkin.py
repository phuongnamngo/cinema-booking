import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.users.models import User

from .exceptions import TicketRejected
from .models import Booking

logger = logging.getLogger(__name__)


def get_ticket(code, *, lock=False):
    """Tìm vé theo mã. lock=True khóa DÒNG BOOKING cho đến hết transaction hiện tại."""
    qs = Booking.objects.select_related(
        "user", "checked_in_by", "showtime__movie", "showtime__room__cinema"
    ).prefetch_related("items__seat")
    if lock:
        # of=("self",): chỉ khóa bảng booking, không khóa suất chiếu/phòng/user đã JOIN.
        # Bắt buộc khi JOIN vào cột nullable (checked_in_by), nếu không Postgres báo lỗi
        qs = qs.select_for_update(of=("self",))
    booking = qs.filter(code=code.strip().upper()).first()
    if booking is None:
        raise NotFound("Không tìm thấy vé với mã này.")
    return booking


def ensure_can_handle(staff, booking):
    """Tầng phân quyền theo đối tượng: staff chỉ xử lý vé của rạp mình."""
    if staff.role == User.Role.ADMIN:
        return
    if staff.cinema_id is None:
        raise PermissionDenied("Tài khoản nhân viên chưa được gán rạp.")
    if staff.cinema_id != booking.showtime.room.cinema_id:
        raise PermissionDenied("Vé này thuộc rạp khác.")


def ticket_problem(booking, now):
    """Trả về TicketRejected nếu vé chưa thể vào rạp, ngược lại None. Hàm này KHÔNG ném lỗi."""
    showtime = booking.showtime

    if booking.status != Booking.Status.CONFIRMED:
        return TicketRejected(
            "not_confirmed", f"Vé chưa hợp lệ (trạng thái: {booking.get_status_display()})."
        )
    if booking.checked_in_at is not None:
        extra = {"checked_in_at": timezone.localtime(booking.checked_in_at).isoformat()}
        if booking.checked_in_by is not None:
            extra["checked_in_by"] = booking.checked_in_by.username
        return TicketRejected("already_checked_in", "Vé này đã được sử dụng.", **extra)
    if not showtime.is_active:
        return TicketRejected("showtime_cancelled", "Suất chiếu đã bị hủy.")

    opens_at = showtime.start_time - timedelta(minutes=settings.CHECKIN_OPENS_BEFORE_MINUTES)
    if now < opens_at:
        return TicketRejected(
            "too_early",
            f"Chưa đến giờ vào rạp (mở từ {timezone.localtime(opens_at):%H:%M %d/%m}).",
        )
    if now > showtime.end_time:
        return TicketRejected("too_late", "Suất chiếu đã kết thúc.")
    return None


@transaction.atomic
def check_in(*, code, staff, now=None):
    now = now or timezone.now()
    booking = get_ticket(code, lock=True)   # người quét thứ hai sẽ chờ ở dòng này

    ensure_can_handle(staff, booking)
    problem = ticket_problem(booking, now)
    if problem is not None:
        raise problem

    booking.checked_in_at = now
    booking.checked_in_by = staff
    booking.save(update_fields=["checked_in_at", "checked_in_by", "updated_at"])
    logger.info("Check-in vé %s bởi %s", booking.code, staff.username)
    return booking
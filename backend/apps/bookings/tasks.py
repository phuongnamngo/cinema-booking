import logging

from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone

from . import services
from .models import Booking

logger = logging.getLogger(__name__)


@shared_task(name="bookings.expire_pending")
def expire_pending_bookings_task():
    """Quét đơn PENDING đã quá hạn: đổi sang EXPIRED, nhả ghế trong DB và phát seats_released.

    Toàn bộ logic nằm ở services.expire_pending_bookings() (đã có từ Bước 6-7).
    Task chỉ là lớp mỏng để gọi định kỳ. Hàm đó dùng select_for_update(skip_locked=True)
    nên hai lần chạy chồng nhau cũng không xử lý trùng.
    """
    ids = services.expire_pending_bookings()
    if ids:
        logger.info("Đã hết hạn %s đơn giữ ghế", len(ids))
    return len(ids)


def _vnd(amount):
    return f"{amount:,}".replace(",", ".") + "đ"


@shared_task(
    name="bookings.send_confirmation_email",
    autoretry_for=(OSError,),
    retry_backoff=5,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)
def send_booking_confirmation_email(booking_id):
    booking = (
        Booking.objects.select_related(
            "user", "voucher", "showtime__movie", "showtime__room__cinema"
        )
        .prefetch_related("items__seat", "combo_lines__combo")
        .filter(
            pk=booking_id, status=Booking.Status.CONFIRMED
        )  # chỉ gửi cho đơn đã xác nhận
        .first()
    )
    if booking is None:
        return

    showtime = booking.showtime
    start = timezone.localtime(showtime.start_time)
    seats = ", ".join(sorted(item.seat.label for item in booking.items.all()))

    lines = [
        "Cảm ơn bạn đã đặt vé!",
        "",
        f"Mã vé: {booking.code}",
        f"Phim: {showtime.movie.title}",
        f"Rạp: {showtime.room.cinema.name} - {showtime.room.name}",
        f"Suất chiếu: {start:%H:%M %d/%m/%Y}",
        f"Ghế: {seats}",
    ]
    combos = ", ".join(
        f"{line.quantity}x {line.combo.name}" for line in booking.combo_lines.all()
    )
    if combos:
        lines.append(f"Combo: {combos}")
    if booking.discount_amount:
        lines.append(
            f"Giảm giá ({booking.voucher.code}): -{_vnd(booking.discount_amount)}"
        )
    lines += [
        f"Tổng tiền: {_vnd(booking.total_amount)}",
        "",
        "Vui lòng đưa mã QR hoặc mã vé cho nhân viên khi vào rạp.",
    ]

    send_mail(
        subject=f"Vé xem phim {showtime.movie.title} - mã {booking.code}",
        message="\n".join(lines),
        from_email=None,
        recipient_list=[booking.user.email],
    )

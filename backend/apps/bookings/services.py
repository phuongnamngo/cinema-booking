import logging
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from redis.exceptions import RedisError
from rest_framework.exceptions import ValidationError

from apps.cinemas.models import Seat
from apps.payments.models import Payment

from collections import defaultdict
from functools import partial

from . import holds, realtime
from .exceptions import (
    BookingNotPending,
    HoldServiceUnavailable,
    PendingBookingExists,
    SeatUnavailable,
)
from .models import Booking, BookingSeat, generate_booking_code

from collections import defaultdict
from functools import partial

logger = logging.getLogger(__name__)


def expire_pending_bookings(**filters):
    """Chuyển booking PENDING đã quá hạn sang EXPIRED và nhả ghế trong DB.

    Đây là "lazy expiration": gọi trước khi đọc/ghi trạng thái ghế nên tính đúng
    không phụ thuộc Celery. Dùng .update() nên KHÔNG tự cập nhật auto_now và
    không phát signal, vì vậy phải set updated_at bằng tay.
    """
    now = timezone.now()
    with transaction.atomic():
        # skip_locked: bỏ qua đơn đang bị khóa (vd: đang được xác nhận thanh toán)
        locked = Booking.objects.select_for_update(skip_locked=True).filter(
            status=Booking.Status.PENDING, expires_at__lte=now, **filters
        )
        ids = [b.id for b in locked.only("id")]
        if not ids:
            return []
        released = defaultdict(list)
        active_items = BookingSeat.objects.filter(booking_id__in=ids, is_active=True)
        for showtime_id, seat_id in active_items.order_by("seat_id").values_list(
            "showtime_id", "seat_id"
        ):
            released[showtime_id].append(seat_id)

        Booking.objects.filter(id__in=ids).update(
            status=Booking.Status.EXPIRED, updated_at=now
        )
        BookingSeat.objects.filter(booking_id__in=ids).update(is_active=False)

        for showtime_id, seat_ids in released.items():
            transaction.on_commit(
                partial(
                    realtime.broadcast_seats, showtime_id, "seats_released", seat_ids
                )
            )
    return ids


def _release_quietly(showtime_id, seat_ids, owner):
    try:
        holds.release_holds(showtime_id, seat_ids, owner)
    except RedisError:
        # Không sao: key sẽ tự hết hạn theo TTL
        logger.warning("Không nhả được hold trên Redis (sẽ tự hết hạn)", exc_info=True)


def hold_seats(*, user, showtime, seat_ids):
    now = timezone.now()

    # 1. Validate
    if not showtime.is_active or showtime.start_time <= now:
        raise ValidationError({"detail": "Suất chiếu đã hủy hoặc đã bắt đầu."})
    seat_ids = list(dict.fromkeys(seat_ids))  # bỏ trùng, giữ thứ tự
    if not 1 <= len(seat_ids) <= settings.MAX_SEATS_PER_BOOKING:
        raise ValidationError(
            {"seat_ids": f"Chọn từ 1 đến {settings.MAX_SEATS_PER_BOOKING} ghế."}
        )
    seats_by_id = {
        s.id: s for s in Seat.objects.filter(id__in=seat_ids, room_id=showtime.room_id)
    }
    if len(seats_by_id) != len(seat_ids):
        raise ValidationError(
            {"seat_ids": "Có ghế không thuộc phòng chiếu của suất này."}
        )

    # 2. Dọn các hold đã hết hạn của suất này
    expire_pending_bookings(showtime=showtime)

    # 3. Mỗi user chỉ giữ một đơn cho mỗi suất
    existing = Booking.objects.filter(
        user=user, showtime=showtime, status=Booking.Status.PENDING
    ).first()
    if existing:
        raise PendingBookingExists(existing.code)

    # 4. Ghế đã có trong DB (đang giữ hoặc đã bán)?
    taken = BookingSeat.objects.filter(
        showtime=showtime, seat_id__in=seat_ids, is_active=True
    ).select_related("seat")
    if taken:
        raise SeatUnavailable(sorted(bs.seat.label for bs in taken))

    # 5. Cổng Redis: giữ tất cả hoặc không ghế nào
    code = generate_booking_code()  # vừa là mã booking, vừa là owner token
    try:
        conflict = holds.acquire_holds(
            showtime.id, seat_ids, owner=code, ttl=settings.SEAT_HOLD_SECONDS
        )
    except RedisError:
        logger.exception("Redis lỗi khi giữ ghế")
        raise HoldServiceUnavailable()
    if conflict is not None:
        raise SeatUnavailable([seats_by_id[conflict].label])

    # 6. Ghi DB. Tính expires_at SAU khi giữ Redis nên key Redis luôn hết hạn trước hoặc cùng lúc
    expires_at = timezone.now() + timedelta(seconds=settings.SEAT_HOLD_SECONDS)
    total = sum(showtime.price_for(seats_by_id[s].seat_type) for s in seat_ids)
    try:
        with transaction.atomic():
            booking = Booking.objects.create(
                code=code,
                user=user,
                showtime=showtime,
                total_amount=total,
                expires_at=expires_at,
            )
            BookingSeat.objects.bulk_create(
                [
                    BookingSeat(
                        booking=booking,
                        showtime=showtime,
                        seat=seats_by_id[s],
                        price=showtime.price_for(seats_by_id[s].seat_type),
                    )
                    for s in seat_ids
                ]
            )
            transaction.on_commit(
                partial(realtime.broadcast_seats, showtime.id, "seats_held", seat_ids)
            )
    except IntegrityError:
        # Unique constraint chặn (race hiếm gặp): nhả Redis rồi báo xung đột
        _release_quietly(showtime.id, seat_ids, code)
        raise SeatUnavailable()
    except Exception:
        _release_quietly(showtime.id, seat_ids, code)
        raise
    return booking


@transaction.atomic
def cancel_pending_booking(booking):
    pending = list(
        Payment.objects.select_for_update().filter(
            booking_id=booking.pk, status=Payment.Status.PENDING
        )
    )
    booking = Booking.objects.select_for_update().get(pk=booking.pk)
    if booking.status != Booking.Status.PENDING:
        raise BookingNotPending()

    booking.status = Booking.Status.CANCELLED
    booking.save(update_fields=["status", "updated_at"])
    booking.items.update(is_active=False)
    for payment in pending:
        payment.status = Payment.Status.CANCELLED
        payment.save(update_fields=["status", "updated_at"])

    seat_ids = list(booking.items.order_by("seat_id").values_list("seat_id", flat=True))
    showtime_id, code = booking.showtime_id, booking.code

    def after_commit():
        _release_quietly(showtime_id, seat_ids, code)
        realtime.broadcast_seats(showtime_id, "seats_released", seat_ids)

    transaction.on_commit(after_commit)
    return booking


def confirm_booking(booking):
    """Đơn đã thanh toán: PENDING -> CONFIRMED.

    Gọi bên trong transaction.atomic, booking đã được select_for_update.
    Các BookingSeat giữ nguyên is_active=True nên unique constraint tiếp tục
    chặn ghế này vĩnh viễn: ghế trở thành 'đã bán'.
    """
    if booking.status != Booking.Status.PENDING:
        raise BookingNotPending()

    booking.status = Booking.Status.CONFIRMED
    booking.save(update_fields=["status", "updated_at"])

    seat_ids = list(booking.items.order_by("seat_id").values_list("seat_id", flat=True))
    showtime_id, code = booking.showtime_id, booking.code

    def after_commit():
        _release_quietly(showtime_id, seat_ids, code)  # khóa Redis không còn cần nữa
        realtime.broadcast_seats(showtime_id, "seats_sold", seat_ids)

    transaction.on_commit(after_commit)

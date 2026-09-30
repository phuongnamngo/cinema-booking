import logging

from celery import shared_task

from . import services

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
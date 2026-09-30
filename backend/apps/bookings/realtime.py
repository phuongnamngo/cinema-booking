import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

# Các event: "seats_held" | "seats_released" | "seats_sold"


def group_name(showtime_id):
    return f"showtime_{showtime_id}"


def broadcast_seats(showtime_id, event, seat_ids):
    """Gọi từ code đồng bộ (view, service, Celery). Không bao giờ được làm hỏng request."""
    layer = get_channel_layer()
    if layer is None or not seat_ids:
        return
    try:
        async_to_sync(layer.group_send)(
            group_name(showtime_id),
            {"type": "seat.event", "event": event, "seat_ids": list(seat_ids)},
        )
    except Exception:
        # Redis layer lỗi thì chỉ mất realtime, dữ liệu vẫn đúng. Client sẽ tự đồng bộ lại khi reconnect
        logger.warning("Không broadcast được %s cho suất %s", event, showtime_id, exc_info=True)
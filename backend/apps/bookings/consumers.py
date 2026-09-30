import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from apps.showtimes.models import Showtime

from .realtime import group_name
from .selectors import get_seat_states

CLOSE_UNAUTHORIZED = 4401   # token sai / hết hạn: refresh rồi kết nối lại
CLOSE_NOT_FOUND = 4404      # suất chiếu không tồn tại / đã đóng: đừng kết nối lại


class SeatMapConsumer(AsyncJsonWebsocketConsumer):
    """ws://.../ws/showtimes/<id>/seats/?token=<access>

    Server -> client:
      {"type": "snapshot", "showtime_id": 1, "held": [..], "mine": [..], "sold": [..]}
      {"type": "seats_held" | "seats_released" | "seats_sold", "seat_ids": [..]}
      {"type": "pong"}
    Client -> server:
      {"type": "ping"}     giữ kết nối, phát hiện kết nối chết
      {"type": "resync"}   yêu cầu gửi lại snapshot
    """

    group = None

    async def connect(self):
        # Accept trước để trình duyệt nhận được close code tùy biến
        await self.accept()

        if self.scope.get("auth_error"):
            await self.close(code=CLOSE_UNAUTHORIZED)
            return

        self.showtime_id = self.scope["url_route"]["kwargs"]["showtime_id"]
        if not await self._showtime_is_open():
            await self.close(code=CLOSE_NOT_FOUND)
            return

        # Vào group TRƯỚC, gửi snapshot SAU, để không sót sự kiện xảy ra giữa chừng
        self.group = group_name(self.showtime_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self._send_snapshot()

    async def disconnect(self, code):
        if self.group:
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        # Dữ liệu từ client là input không tin cậy: JSON rác thì bỏ qua, không được làm sập consumer
        try:
            content = json.loads(text_data or "")
        except ValueError:
            return
        await self.receive_json(content)

    async def receive_json(self, content, **kwargs):
        kind = content.get("type") if isinstance(content, dict) else None
        if kind == "ping":
            await self.send_json({"type": "pong"})
        elif kind == "resync":
            await self._send_snapshot()

    # Được gọi khi group_send có "type": "seat.event"
    async def seat_event(self, event):
        await self.send_json({"type": event["event"], "seat_ids": event["seat_ids"]})

    async def _send_snapshot(self):
        states = await self._seat_states()
        await self.send_json({"type": "snapshot", "showtime_id": self.showtime_id, **states})

    @database_sync_to_async
    def _showtime_is_open(self):
        return Showtime.objects.filter(
            pk=self.showtime_id, is_active=True, start_time__gt=timezone.now()
        ).exists()

    @database_sync_to_async
    def _seat_states(self):
        states = get_seat_states(self.showtime_id, self.scope["user"])
        result = {"held": [], "mine": [], "sold": []}
        for seat_id, state in sorted(states.items()):
            result[state].append(seat_id)
        return result
from datetime import timedelta

from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from apps.users.models import User
from apps.users.ws_auth import JWTAuthMiddleware

from .models import Booking, BookingSeat
from .realtime import group_name
from .routing import websocket_urlpatterns
from .tests import build_showtime, seat

TEST_CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
class SeatMapConsumerTests(TransactionTestCase):
    def setUp(self):
        # Mọi thao tác DB làm ở setUp (đồng bộ). Test async chỉ nói chuyện qua WebSocket
        self.alice = User.objects.create(username="alice", email="alice@example.com")
        self.showtime = build_showtime()
        self.a1, self.a2 = seat(self.showtime, "A", 1), seat(self.showtime, "A", 2)

        booking = Booking.objects.create(
            user=self.alice, showtime=self.showtime, total_amount=80000,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        BookingSeat.objects.create(
            booking=booking, showtime=self.showtime, seat=self.a1, price=80000
        )

        self.alice_token = str(AccessToken.for_user(self.alice))
        expired = AccessToken.for_user(self.alice)
        expired.set_exp(from_time=timezone.now() - timedelta(hours=1))   # hết hạn từ 45 phút trước
        self.expired_token = str(expired)

        self.app = JWTAuthMiddleware(URLRouter(websocket_urlpatterns))

    def communicator(self, showtime_id=None, token=None):
        path = f"/ws/showtimes/{showtime_id or self.showtime.id}/seats/"
        if token:
            path += f"?token={token}"
        return WebsocketCommunicator(self.app, path)

    def snapshot(self, **states):
        base = {"type": "snapshot", "showtime_id": self.showtime.id,
                "held": [], "mine": [], "sold": []}
        return {**base, **states}

    async def test_anonymous_sees_seat_as_held(self):
        comm = self.communicator()
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        self.assertEqual(await comm.receive_json_from(), self.snapshot(held=[self.a1.id]))
        await comm.disconnect()

    async def test_owner_sees_seat_as_mine(self):
        comm = self.communicator(token=self.alice_token)
        await comm.connect()
        self.assertEqual(await comm.receive_json_from(), self.snapshot(mine=[self.a1.id]))
        await comm.disconnect()

    async def test_group_event_is_forwarded_to_client(self):
        comm = self.communicator()
        await comm.connect()
        await comm.receive_json_from()   # bỏ qua snapshot

        await get_channel_layer().group_send(
            group_name(self.showtime.id),
            {"type": "seat.event", "event": "seats_held", "seat_ids": [self.a2.id]},
        )
        self.assertEqual(
            await comm.receive_json_from(), {"type": "seats_held", "seat_ids": [self.a2.id]}
        )
        await comm.disconnect()

    async def test_ping_resync_and_garbage_message(self):
        comm = self.communicator()
        await comm.connect()
        await comm.receive_json_from()

        await comm.send_json_to({"type": "ping"})
        self.assertEqual(await comm.receive_json_from(), {"type": "pong"})

        await comm.send_json_to({"type": "resync"})
        self.assertEqual((await comm.receive_json_from())["type"], "snapshot")

        await comm.send_to(text_data="đây không phải JSON")   # không được làm sập kết nối
        await comm.send_json_to({"type": "ping"})
        self.assertEqual(await comm.receive_json_from(), {"type": "pong"})
        await comm.disconnect()

    async def test_bad_or_expired_token_closes_with_4401(self):
        for token in ("garbage", self.expired_token):
            comm = self.communicator(token=token)
            connected, _ = await comm.connect()
            self.assertTrue(connected)   # đã accept để trình duyệt nhận được close code
            out = await comm.receive_output()
            self.assertEqual((out["type"], out["code"]), ("websocket.close", 4401))
            await comm.disconnect()

    async def test_unknown_showtime_closes_with_4404(self):
        comm = self.communicator(showtime_id=999999)
        await comm.connect()
        out = await comm.receive_output()
        self.assertEqual((out["type"], out["code"]), ("websocket.close", 4404))
        await comm.disconnect()
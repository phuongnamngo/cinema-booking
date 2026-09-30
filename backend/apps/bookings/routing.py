from django.urls import path

from .consumers import SeatMapConsumer

websocket_urlpatterns = [
    path("ws/showtimes/<int:showtime_id>/seats/", SeatMapConsumer.as_asgi()),
]
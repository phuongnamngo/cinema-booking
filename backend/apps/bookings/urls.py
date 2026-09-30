from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import BookingViewSet, HoldSeatsView

router = SimpleRouter()
router.register("bookings", BookingViewSet, basename="booking")

urlpatterns = [
    path("showtimes/<int:showtime_id>/hold/", HoldSeatsView.as_view(), name="showtime-hold"),
    *router.urls,
]
from django.urls import path
from rest_framework.routers import SimpleRouter

from .staff_views import CheckInView, TicketLookupView
from .views import BookingViewSet, HoldSeatsView

router = SimpleRouter()
router.register("bookings", BookingViewSet, basename="booking")

urlpatterns = [
    path("showtimes/<int:showtime_id>/hold/", HoldSeatsView.as_view(), name="showtime-hold"),
    path("staff/tickets/<str:code>/", TicketLookupView.as_view(), name="staff-ticket"),
    path("staff/checkin/", CheckInView.as_view(), name="staff-checkin"),
    *router.urls,
]
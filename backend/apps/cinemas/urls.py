from rest_framework.routers import SimpleRouter

from .views import CinemaViewSet, RoomViewSet

router = SimpleRouter()
router.register("cinemas", CinemaViewSet, basename="cinema")
router.register("rooms", RoomViewSet, basename="room")

urlpatterns = router.urls
from rest_framework.routers import SimpleRouter

from .views import ShowtimeViewSet

router = SimpleRouter()
router.register("showtimes", ShowtimeViewSet, basename="showtime")

urlpatterns = router.urls
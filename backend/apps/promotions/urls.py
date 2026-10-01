from rest_framework.routers import SimpleRouter

from .views import ComboViewSet

router = SimpleRouter()
router.register("combos", ComboViewSet, basename="combo")

urlpatterns = router.urls
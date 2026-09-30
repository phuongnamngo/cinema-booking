from rest_framework.routers import SimpleRouter

from .views import GenreViewSet, MovieViewSet

router = SimpleRouter()
router.register("genres", GenreViewSet, basename="genre")
router.register("movies", MovieViewSet, basename="movie")

urlpatterns = router.urls
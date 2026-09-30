from rest_framework import viewsets

from apps.users.permissions import IsAdminOrReadOnly

from .filters import MovieFilter
from .models import Genre, Movie
from .serializers import GenreSerializer, MovieSerializer


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None   # thể loại ít, trả hết một lần


class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.prefetch_related("genres")
    serializer_class = MovieSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = MovieFilter
    search_fields = ["title", "synopsis"]
    ordering_fields = ["release_date", "title"]
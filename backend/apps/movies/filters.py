from django_filters import rest_framework as filters

from .models import Movie


class MovieFilter(filters.FilterSet):
    genre = filters.NumberFilter(field_name="genres__id")
    release_from = filters.DateFilter(field_name="release_date", lookup_expr="gte")
    release_to = filters.DateFilter(field_name="release_date", lookup_expr="lte")

    class Meta:
        model = Movie
        fields = ["status", "age_rating"]
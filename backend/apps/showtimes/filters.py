from datetime import datetime, time, timedelta

from django.utils import timezone
from django_filters import rest_framework as filters

from .models import Showtime


class ShowtimeFilter(filters.FilterSet):
    cinema = filters.NumberFilter(field_name="room__cinema_id")
    city = filters.CharFilter(field_name="room__cinema__city", lookup_expr="iexact")
    date = filters.DateFilter(method="filter_date")

    class Meta:
        model = Showtime
        fields = ["movie", "room"]

    def filter_date(self, queryset, name, value):
        # 00:00 -> 24:00 của ngày đó theo giờ Việt Nam
        start = timezone.make_aware(datetime.combine(value, time.min))
        return queryset.filter(start_time__gte=start, start_time__lt=start + timedelta(days=1))
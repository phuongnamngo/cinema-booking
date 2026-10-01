from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers


class DateRangeSerializer(serializers.Serializer):
    """Tham số ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD (gồm cả hai đầu). Mặc định: 7 ngày gần nhất."""

    max_days = 92

    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, attrs):
        date_to = attrs.get("date_to") or timezone.localdate()
        date_from = attrs.get("date_from") or date_to - timedelta(days=6)
        if date_from > date_to:
            raise serializers.ValidationError({"date_from": "date_from phải trước hoặc bằng date_to."})
        if (date_to - date_from).days + 1 > self.max_days:
            raise serializers.ValidationError(
                {"date_to": f"Khoảng thời gian tối đa {self.max_days} ngày."}
            )
        return {**attrs, "date_from": date_from, "date_to": date_to}


class TopMoviesParamsSerializer(DateRangeSerializer):
    limit = serializers.IntegerField(min_value=1, max_value=20, default=5)


class OccupancyParamsSerializer(DateRangeSerializer):
    max_days = 31   # mỗi suất chiếu là một dòng, giữ kết quả ở mức hợp lý


class RevenuePointSerializer(serializers.Serializer):
    date = serializers.DateField()
    revenue = serializers.IntegerField()
    orders = serializers.IntegerField()


class RevenueReportSerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    total_revenue = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    days = RevenuePointSerializer(many=True)


class TopMovieSerializer(serializers.Serializer):
    movie_id = serializers.IntegerField()
    title = serializers.CharField()
    tickets = serializers.IntegerField()
    revenue = serializers.IntegerField()


class TopMoviesReportSerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    movies = TopMovieSerializer(many=True)


class OccupancyRowSerializer(serializers.Serializer):
    showtime_id = serializers.IntegerField()
    movie_title = serializers.CharField()
    cinema_name = serializers.CharField()
    room_name = serializers.CharField()
    start_time = serializers.DateTimeField()
    seats_total = serializers.IntegerField()
    seats_sold = serializers.IntegerField()
    occupancy = serializers.FloatField()


class OccupancyReportSerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    overall_occupancy = serializers.FloatField()
    showtimes = OccupancyRowSerializer(many=True)
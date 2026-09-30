from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.cinemas.serializers import SeatSerializer

from .models import Showtime
from .services import validate_schedule


class ShowtimeSerializer(serializers.ModelSerializer):
    movie_title = serializers.CharField(source="movie.title", read_only=True)
    room_name = serializers.CharField(source="room.name", read_only=True)
    cinema_id = serializers.IntegerField(source="room.cinema_id", read_only=True)
    cinema_name = serializers.CharField(source="room.cinema.name", read_only=True)

    class Meta:
        model = Showtime
        fields = (
            "id",
            "movie",
            "movie_title",
            "room",
            "room_name",
            "cinema_id",
            "cinema_name",
            "start_time",
            "end_time",
            "price_standard",
            "price_vip",
            "price_couple",
            "is_active",
        )

    def validate(self, attrs):
        instance = self.instance

        # PATCH chỉ đổi giá hoặc is_active thì không cần kiểm tra lịch
        if instance and not ({"movie", "room", "start_time"} & attrs.keys()):
            return attrs

        validate_schedule(
            movie=attrs.get("movie", getattr(instance, "movie", None)),
            room=attrs.get("room", getattr(instance, "room", None)),
            start_time=attrs.get("start_time", getattr(instance, "start_time", None)),
            exclude_id=instance.pk if instance else None,
            check_past="start_time" in attrs,
        )
        return attrs


class ShowtimeSeatSerializer(SeatSerializer):
    """Ghế kèm giá và trạng thái theo suất chiếu."""

    price = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta(SeatSerializer.Meta):
        fields = SeatSerializer.Meta.fields + ("price", "status")

    @extend_schema_field(int)
    def get_price(self, seat):
        return self.context["showtime"].price_for(seat.seat_type)

    @extend_schema_field(
        serializers.ChoiceField(choices=["available", "held", "mine", "sold"])
    )
    def get_status(self, seat):
        return self.context["seat_states"].get(seat.id, "available")

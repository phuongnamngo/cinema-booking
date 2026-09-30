import string

from rest_framework import serializers

from .models import Cinema, Room, Seat


class CinemaSerializer(serializers.ModelSerializer):
    rooms_count = serializers.IntegerField(read_only=True)   # do annotate() ở view cấp

    class Meta:
        model = Cinema
        fields = ("id", "name", "address", "city", "phone", "is_active", "rooms_count")


class RoomSerializer(serializers.ModelSerializer):
    seats_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Room
        fields = ("id", "cinema", "name", "is_active", "seats_count")


class SeatSerializer(serializers.ModelSerializer):
    label = serializers.CharField(read_only=True)

    class Meta:
        model = Seat
        fields = ("id", "row", "number", "label", "seat_type")


class GenerateSeatsSerializer(serializers.Serializer):
    rows = serializers.IntegerField(min_value=1, max_value=26)
    seats_per_row = serializers.IntegerField(min_value=1, max_value=30)
    vip_rows = serializers.ListField(
        child=serializers.CharField(max_length=1), required=False, default=list
    )
    couple_rows = serializers.ListField(
        child=serializers.CharField(max_length=1), required=False, default=list
    )

    def validate(self, attrs):
        valid = set(string.ascii_uppercase[: attrs["rows"]])
        attrs["vip_rows"] = [r.upper() for r in attrs["vip_rows"]]
        attrs["couple_rows"] = [r.upper() for r in attrs["couple_rows"]]

        for name in ("vip_rows", "couple_rows"):
            invalid = set(attrs[name]) - valid
            if invalid:
                raise serializers.ValidationError({name: f"Hàng không tồn tại: {sorted(invalid)}"})
        if set(attrs["vip_rows"]) & set(attrs["couple_rows"]):
            raise serializers.ValidationError("Một hàng không thể vừa VIP vừa ghế đôi.")
        return attrs
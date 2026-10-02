from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.payments.models import Payment

from .models import Booking, BookingSeat, BookingCombo


class HoldSeatsSerializer(serializers.Serializer):
    seat_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=settings.MAX_SEATS_PER_BOOKING,
    )

    def validate_seat_ids(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Danh sách ghế bị trùng.")
        return value


class BookingSeatSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="seat.label", read_only=True)
    seat_type = serializers.CharField(source="seat.seat_type", read_only=True)

    class Meta:
        model = BookingSeat
        fields = ("seat", "label", "seat_type", "price")


class BookingComboSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="combo.name", read_only=True)
    line_total = serializers.IntegerField(read_only=True)

    class Meta:
        model = BookingCombo
        fields = ("combo", "name", "quantity", "unit_price", "line_total")
        read_only_fields = fields


class ComboLineSerializer(serializers.Serializer):
    combo = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=10)


class SetCombosSerializer(serializers.Serializer):
    items = ComboLineSerializer(many=True, allow_empty=True, max_length=10)


class ApplyVoucherSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=32)


class BookingSerializer(serializers.ModelSerializer):
    seats = BookingSeatSerializer(source="items", many=True, read_only=True)
    combos = BookingComboSerializer(source="combo_lines", many=True, read_only=True)
    movie_title = serializers.CharField(source="showtime.movie.title", read_only=True)
    cinema_name = serializers.CharField(source="showtime.room.cinema.name", read_only=True)
    room_name = serializers.CharField(source="showtime.room.name", read_only=True)
    start_time = serializers.DateTimeField(source="showtime.start_time", read_only=True)
    seconds_left = serializers.SerializerMethodField()
    seats_amount = serializers.SerializerMethodField()
    combos_amount = serializers.SerializerMethodField()
    voucher_code = serializers.SerializerMethodField()
    has_pending_payment = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            "id", "code", "status", "total_amount", "seats_amount", "combos_amount",
            "discount_amount", "voucher_code", "expires_at", "checked_in_at", "seconds_left",
            "showtime", "movie_title", "cinema_name", "room_name", "start_time",
            "seats", "combos", "created_at", "has_pending_payment",
        )
        read_only_fields = fields

    @extend_schema_field(int)
    def get_seconds_left(self, booking):
        if booking.status != Booking.Status.PENDING:
            return 0
        return max(0, int((booking.expires_at - timezone.now()).total_seconds()))

    # Tính trên dữ liệu đã prefetch: không phát sinh query mới cho mỗi đơn
    @extend_schema_field(int)
    def get_seats_amount(self, booking):
        return sum(item.price for item in booking.items.all())

    @extend_schema_field(int)
    def get_combos_amount(self, booking):
        return sum(line.line_total for line in booking.combo_lines.all())

    @extend_schema_field(str)
    def get_voucher_code(self, booking):
        return booking.voucher.code if booking.voucher_id else None

    @extend_schema_field(bool)
    def get_has_pending_payment(self, booking):
        return any(
            payment.status == Payment.Status.PENDING for payment in booking.payments.all()
        )


class CheckInSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=12)


class TicketSerializer(serializers.ModelSerializer):
    """Thông tin vé dành cho nhân viên soát vé."""

    seats = BookingSeatSerializer(source="items", many=True, read_only=True)
    movie_title = serializers.CharField(source="showtime.movie.title", read_only=True)
    cinema_name = serializers.CharField(
        source="showtime.room.cinema.name", read_only=True
    )
    room_name = serializers.CharField(source="showtime.room.name", read_only=True)
    start_time = serializers.DateTimeField(source="showtime.start_time", read_only=True)
    end_time = serializers.DateTimeField(source="showtime.end_time", read_only=True)
    customer = serializers.SerializerMethodField()
    checked_in_by = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            "code",
            "status",
            "movie_title",
            "cinema_name",
            "room_name",
            "start_time",
            "end_time",
            "seats",
            "customer",
            "checked_in_at",
            "checked_in_by",
        )
        read_only_fields = fields

    @extend_schema_field(str)
    def get_customer(self, booking):
        return booking.user.get_full_name() or booking.user.username

    @extend_schema_field(str)
    def get_checked_in_by(self, booking):
        return booking.checked_in_by.username if booking.checked_in_by else None

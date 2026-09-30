from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.showtimes.models import Showtime

from .models import Booking
from .selectors import bookings_with_details
from .serializers import BookingSerializer, HoldSeatsSerializer
from .services import cancel_pending_booking, expire_pending_bookings, hold_seats


class HoldSeatsView(APIView):
    """POST /showtimes/{id}/hold/ - giữ ghế. Đặt ở app bookings (không phải @action của
    ShowtimeViewSet) vì customer cần quyền ghi, còn ShowtimeViewSet chỉ cho admin ghi."""

    @extend_schema(request=HoldSeatsSerializer, responses={201: BookingSerializer})
    def post(self, request, showtime_id):
        showtime = get_object_or_404(
            Showtime.objects.select_related("movie", "room__cinema"),
            pk=showtime_id, is_active=True,
        )
        serializer = HoldSeatsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking = hold_seats(
            user=request.user, showtime=showtime,
            seat_ids=serializer.validated_data["seat_ids"],
        )
        booking = bookings_with_details().get(pk=booking.pk)
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Đơn đặt vé của chính người dùng đang đăng nhập."""

    serializer_class = BookingSerializer
    lookup_field = "code"
    filterset_fields = ["status"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):   # drf-spectacular tự dò schema
            return Booking.objects.none()
        expire_pending_bookings(user=self.request.user)   # cập nhật trạng thái đơn hết hạn của user
        return bookings_with_details().filter(user=self.request.user)

    @extend_schema(request=None, responses=BookingSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, code=None):
        """POST /bookings/{code}/cancel/ - hủy đơn đang giữ ghế và nhả ghế."""
        booking = self.get_object()
        cancel_pending_booking(booking)
        booking = bookings_with_details().get(pk=booking.pk)
        return Response(self.get_serializer(booking).data)
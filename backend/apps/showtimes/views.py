from django.db import IntegrityError, transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from apps.bookings.selectors import get_seat_states

from apps.users.permissions import IsAdminOrReadOnly, is_admin

from .filters import ShowtimeFilter
from .models import Showtime
from .serializers import ShowtimeSeatSerializer, ShowtimeSerializer


class ShowtimePagination(PageNumberPagination):
    page_size = 50  # lịch chiếu một ngày thường nhiều hơn 12
    page_size_query_param = "page_size"
    max_page_size = 200


class ShowtimeViewSet(viewsets.ModelViewSet):
    serializer_class = ShowtimeSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = ShowtimePagination
    filterset_class = ShowtimeFilter
    ordering_fields = ["start_time"]
    http_method_names = [
        "get",
        "post",
        "put",
        "patch",
        "head",
        "options",
    ]  # hủy = PATCH is_active

    def get_queryset(self):
        qs = Showtime.objects.select_related("movie", "room__cinema")
        if not is_admin(self.request.user):
            # Khách chỉ thấy suất còn hiệu lực và chưa chiếu
            qs = qs.filter(is_active=True, start_time__gt=timezone.now())
        return qs

    def _save(self, serializer):
        # Lớp cuối: nếu lọt qua kiểm tra ở serializer (race condition) thì DB chặn
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            raise ValidationError(
                {"detail": "Xung đột lịch chiếu trong phòng, vui lòng thử lại."}
            )

    def perform_create(self, serializer):
        self._save(serializer)

    def perform_update(self, serializer):
        self._save(serializer)

    @extend_schema(responses=ShowtimeSeatSerializer(many=True))
    @action(detail=True, methods=["get"])
    def seats(self, request, pk=None):
        """GET /showtimes/{id}/seats/ - sơ đồ ghế kèm giá của suất chiếu."""
        showtime = self.get_object()
        serializer = ShowtimeSeatSerializer(
            showtime.room.seats.all(),
            many=True,
            context={
                "showtime": showtime,
                "seat_states": get_seat_states(showtime, request.user),
            },
        )
        return Response(serializer.data)

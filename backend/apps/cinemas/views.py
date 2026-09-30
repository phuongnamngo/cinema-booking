from django.db.models import Count
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.permissions import IsAdminOrReadOnly, is_admin

from .models import Cinema, Room
from .serializers import (
    CinemaSerializer,
    GenerateSeatsSerializer,
    RoomSerializer,
    SeatSerializer,
)
from .services import generate_seats

# Không cho DELETE: rạp/phòng sẽ được "ngừng hoạt động" bằng is_active
NO_DELETE = ["get", "post", "put", "patch", "head", "options"]


class CinemaViewSet(viewsets.ModelViewSet):
    serializer_class = CinemaSerializer
    permission_classes = [IsAdminOrReadOnly]
    http_method_names = NO_DELETE
    filterset_fields = ["city"]
    search_fields = ["name", "address"]

    def get_queryset(self):
        qs = Cinema.objects.annotate(rooms_count=Count("rooms"))
        if not is_admin(self.request.user):
            qs = qs.filter(is_active=True)   # khách chỉ thấy rạp đang hoạt động
        return qs


class RoomViewSet(viewsets.ModelViewSet):
    serializer_class = RoomSerializer
    permission_classes = [IsAdminOrReadOnly]
    http_method_names = NO_DELETE
    filterset_fields = ["cinema"]

    def get_queryset(self):
        return Room.objects.annotate(seats_count=Count("seats"))

    @extend_schema(responses=SeatSerializer(many=True))
    @action(detail=True, methods=["get"])
    def seats(self, request, pk=None):
        """GET /rooms/{id}/seats/ - sơ đồ ghế của phòng."""
        room = self.get_object()
        return Response(SeatSerializer(room.seats.all(), many=True).data)

    @extend_schema(request=GenerateSeatsSerializer, responses={201: None})
    @action(detail=True, methods=["post"], url_path="generate-seats")
    def generate_seats(self, request, pk=None):
        """POST /rooms/{id}/generate-seats/ - sinh sơ đồ ghế tự động."""
        room = self.get_object()
        serializer = GenerateSeatsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if room.seats.exists():
            return Response(
                {"detail": "Phòng đã có sơ đồ ghế."}, status=status.HTTP_409_CONFLICT
            )

        seats = generate_seats(room, **serializer.validated_data)
        return Response({"created": len(seats)}, status=status.HTTP_201_CREATED)
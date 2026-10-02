from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsStaffOrAdmin

from .checkin import check_in, ensure_can_handle, get_ticket, ticket_problem
from .serializers import CheckInSerializer, TicketSerializer


class TicketLookupView(APIView):
    """GET /staff/tickets/{code}/ - xem vé và biết có check-in được không (KHÔNG thay đổi gì)."""

    permission_classes = [IsStaffOrAdmin]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, code):
        booking = get_ticket(code)
        ensure_can_handle(request.user, booking)
        problem = ticket_problem(booking, timezone.now())
        return Response({
            "ticket": TicketSerializer(booking).data,
            "can_check_in": problem is None,
            "reason": problem.reason if problem else None,
            "message": problem.message if problem else None,
        })


class CheckInView(APIView):
    """POST /staff/checkin/ {"code": "..."} - xác nhận khách vào rạp."""

    permission_classes = [IsStaffOrAdmin]
    throttle_scope = "checkin"

    @extend_schema(request=CheckInSerializer, responses=TicketSerializer)
    def post(self, request):
        serializer = CheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = check_in(code=serializer.validated_data["code"], staff=request.user)
        return Response(TicketSerializer(booking).data)
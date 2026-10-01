from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdmin

from . import selectors
from .serializers import (
    DateRangeSerializer,
    OccupancyParamsSerializer,
    OccupancyReportSerializer,
    RevenueReportSerializer,
    TopMoviesParamsSerializer,
    TopMoviesReportSerializer,
)


class ReportView(APIView):
    """Khung chung: chỉ admin, đọc tham số từ query string, trả về serializer đầu ra."""

    permission_classes = [IsAdmin]
    params_serializer = DateRangeSerializer
    output_serializer = None
    selector = None

    def get(self, request):
        params = self.params_serializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        report = type(self).selector(**params.validated_data)
        return Response(self.output_serializer(report).data)


class RevenueReportView(ReportView):
    params_serializer = DateRangeSerializer
    output_serializer = RevenueReportSerializer
    selector = staticmethod(selectors.revenue_report)

    @extend_schema(parameters=[DateRangeSerializer], responses=RevenueReportSerializer)
    def get(self, request):
        return super().get(request)


class TopMoviesReportView(ReportView):
    params_serializer = TopMoviesParamsSerializer
    output_serializer = TopMoviesReportSerializer
    selector = staticmethod(selectors.top_movies)

    @extend_schema(parameters=[TopMoviesParamsSerializer], responses=TopMoviesReportSerializer)
    def get(self, request):
        return super().get(request)


class OccupancyReportView(ReportView):
    params_serializer = OccupancyParamsSerializer
    output_serializer = OccupancyReportSerializer
    selector = staticmethod(selectors.showtime_occupancy)

    @extend_schema(parameters=[OccupancyParamsSerializer], responses=OccupancyReportSerializer)
    def get(self, request):
        return super().get(request)
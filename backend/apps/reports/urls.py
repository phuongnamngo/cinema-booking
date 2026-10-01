from django.urls import path

from .views import OccupancyReportView, RevenueReportView, TopMoviesReportView

urlpatterns = [
    path("reports/revenue/", RevenueReportView.as_view(), name="report-revenue"),
    path("reports/top-movies/", TopMoviesReportView.as_view(), name="report-top-movies"),
    path("reports/occupancy/", OccupancyReportView.as_view(), name="report-occupancy"),
]
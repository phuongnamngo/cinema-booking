from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.payments.views import MockGatewayView

urlpatterns = [
    path("", include("apps.core.urls")),  # /healthz, /readyz
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.users.urls")),
    path("api/v1/", include("apps.movies.urls")),
    path("api/v1/", include("apps.cinemas.urls")),
    path("api/v1/", include("apps.showtimes.urls")),
    path("api/v1/", include("apps.bookings.urls")),
    path("api/v1/", include("apps.payments.urls")),
    path("api/v1/", include("apps.reports.urls")),
    path("api/v1/", include("apps.promotions.urls")),
    path("mock-gateway/<str:txn_ref>/", MockGatewayView.as_view(), name="mock-gateway"),
]

if settings.ENABLE_API_DOCS:  # production không phơi tài liệu API ra internet
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"
        ),
    ]

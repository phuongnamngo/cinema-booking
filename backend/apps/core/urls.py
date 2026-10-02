from django.urls import path

from .views import healthz, readyz

urlpatterns = [
    path("healthz", healthz),
    path("readyz", readyz),
]
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from .health import run_checks


@require_safe
def healthz(request):
    """Liveness: process còn chạy. Cố tình KHÔNG đụng DB hay Redis."""
    return JsonResponse({"status": "ok"})


@never_cache
@require_safe
def readyz(request):
    """Readiness: có phục vụ được không. 503 khi một phụ thuộc hỏng."""
    results = run_checks()
    ok = all(value == "ok" for value in results.values())
    return JsonResponse({"status": "ok" if ok else "fail", **results}, status=200 if ok else 503)
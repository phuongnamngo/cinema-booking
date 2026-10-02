import logging
import re
import time
import uuid

import sentry_sdk

from .logs import request_id_var

access_logger = logging.getLogger("apps.core.access")

# Chỉ nhận request id từ proxy khi có dạng an toàn, để chặn log injection.
# Dùng fullmatch: "$" của regex khớp cả trước dấu xuống dòng ở cuối chuỗi, nên match() sẽ để lọt "abc12345\n"
VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{8,64}")

# Probe của Docker/Nginx gọi mỗi vài giây: không ghi log ở mức INFO để khỏi lấp mất log thật
QUIET_PATHS = frozenset({"/healthz", "/readyz"})


class RequestContextMiddleware:
    """Gắn request id, đo thời gian và ghi MỘT dòng access log cho mỗi request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if VALID_REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        request.request_id = request_id
        sentry_sdk.set_tag("request_id", request_id)   # không làm gì nếu Sentry chưa bật

        started = time.monotonic()
        status = 500   # chỉ còn nguyên giá trị này nếu có gì ném lỗi xuyên qua middleware
        try:
            response = self.get_response(request)
            status = response.status_code
            response["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = round((time.monotonic() - started) * 1000)
            user = getattr(request, "user", None)   # DRF gán user vào request gốc sau khi xác thực
            user_id = user.pk if getattr(user, "is_authenticated", False) else None
            level = logging.DEBUG if request.path in QUIET_PATHS else logging.INFO
            access_logger.log(
                level,
                "%s %s %s %sms", request.method, request.path, status, duration_ms,
                # CHỈ path, không bao giờ query string (có thể chứa token)
                extra={
                    "method": request.method, "path": request.path, "status": status,
                    "duration_ms": duration_ms, "user_id": user_id,
                },
            )
            request_id_var.reset(token)
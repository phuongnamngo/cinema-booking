import logging

from redis.exceptions import RedisError
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle

logger = logging.getLogger(__name__)


class FailOpenMixin:
    """Giới hạn tốc độ là lớp bảo vệ PHỤ: cache lỗi thì cho request đi qua thay vì làm sập cả API."""

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except RedisError as exc:
            logger.warning(
                "Cache lỗi (%s): bỏ qua giới hạn tốc độ cho request này", type(exc).__name__
            )
            return True


class AnonThrottle(FailOpenMixin, AnonRateThrottle):
    """Khách chưa đăng nhập, đếm theo IP (scope "anon")."""


class UserThrottle(FailOpenMixin, UserRateThrottle):
    """Người đã đăng nhập, đếm theo user id (scope "user"). Khách để AnonThrottle lo,
    nếu không mỗi request ẩn danh bị đếm hai lần."""

    def get_cache_key(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return None
        return super().get_cache_key(request, view)


class ScopedThrottle(FailOpenMixin, ScopedRateThrottle):
    """Giới hạn riêng cho view khai báo `throttle_scope`. Scope không có trong
    DEFAULT_THROTTLE_RATES sẽ báo lỗi cấu hình ngay lần gọi đầu tiên."""
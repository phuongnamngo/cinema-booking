from unittest.mock import patch

import redis
from rest_framework.throttling import SimpleRateThrottle


def rates(**overrides):
    """Hạ giới hạn của vài scope trong lúc test. Dùng như context manager hoặc decorator.
    Khi chạy test, mọi scope mặc định là 1.000.000/phút nên test khác không bị vướng."""
    return patch.dict(SimpleRateThrottle.THROTTLE_RATES, overrides)


class BrokenCache:
    """Giả lập cache (Redis) đã sập."""

    def get(self, *args, **kwargs):
        raise redis.exceptions.ConnectionError("Redis đã sập")

    set = get
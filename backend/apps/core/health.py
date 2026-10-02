import logging

import redis
from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)


def check_database():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()


def check_redis():
    # Timeout ngắn: Redis treo mà probe treo theo thì probe vô nghĩa
    client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
    try:
        client.ping()
    finally:
        client.close()


def run_checks():
    """Trả về {"database": "ok"|"fail", "redis": "ok"|"fail"}. Chi tiết lỗi chỉ vào log, KHÔNG ra response."""
    results = {}
    for name, check in (("database", check_database), ("redis", check_redis)):
        try:
            check()
            results[name] = "ok"
        except Exception:
            logger.exception("Health check '%s' thất bại", name)
            results[name] = "fail"
    return results
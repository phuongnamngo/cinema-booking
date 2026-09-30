# Nạp Celery app khi Django khởi động để @shared_task gắn đúng app
from .celery import app as celery_app

__all__ = ("celery_app",)
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("cinema")
# Đọc mọi setting có tiền tố CELERY_ từ settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")
# Tự tìm file tasks.py trong các app trong INSTALLED_APPS
app.autodiscover_tasks()
import sentry_sdk
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Gửi một sự kiện thử lên Sentry để kiểm tra DSN"

    def handle(self, *args, **options):
        if not settings.SENTRY_DSN:
            raise CommandError("Chưa cấu hình SENTRY_DSN.")
        event_id = sentry_sdk.capture_message("Sentry check từ Cinema Booking", level="info")
        sentry_sdk.flush(timeout=5)
        self.stdout.write(self.style.SUCCESS(f"Đã gửi sự kiện {event_id}"))
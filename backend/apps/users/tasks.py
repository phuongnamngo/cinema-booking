from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management import call_command


@shared_task(
    name="users.send_welcome_email",
    autoretry_for=(OSError,),   # lỗi kết nối/SMTP (SMTPException cũng là OSError)
    retry_backoff=5,            # chờ ~5s, 10s, 20s, 40s, 80s (có jitter ngẫu nhiên)
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)
def send_welcome_email(user_id):
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return   # user đã bị xóa trong lúc chờ, không còn gì để gửi

    send_mail(
        subject="Chào mừng bạn đến với Cinema Booking",
        message=(
            f"Xin chào {user.first_name or user.username},\n\n"
            "Tài khoản của bạn đã được tạo thành công. "
            "Chúc bạn có những buổi xem phim thật vui!\n\n"
            "Cinema Booking"
        ),
        from_email=None,   # dùng DEFAULT_FROM_EMAIL
        recipient_list=[user.email],
    )


@shared_task(name="users.flush_expired_tokens")
def flush_expired_tokens():
    """Xóa refresh token đã hết hạn khỏi bảng token_blacklist (bảng này phình dần theo thời gian)."""
    call_command("flushexpiredtokens")
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _get_active_user(user_id):
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None
    return user if user.is_active else None


class JWTAuthMiddleware(BaseMiddleware):
    """Đọc ?token=<access> từ query string và gắn vào scope.

    - Không có token       -> scope["user"] = AnonymousUser (vẫn được xem sơ đồ ghế)
    - Token sai/hết hạn    -> scope["auth_error"] = True (consumer sẽ đóng với mã 4401)
    """

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        scope["user"] = AnonymousUser()
        scope["auth_error"] = False

        query = parse_qs(scope.get("query_string", b"").decode())
        token = (query.get("token") or [None])[0]
        if token:
            try:
                validated = AccessToken(token)   # kiểm tra chữ ký, hạn dùng, loại token
                user = await _get_active_user(validated[api_settings.USER_ID_CLAIM])
            except TokenError:
                user = None
            if user is None:
                scope["auth_error"] = True
            else:
                scope["user"] = user

        return await self.inner(scope, receive, send)
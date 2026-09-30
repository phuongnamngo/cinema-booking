"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Phải khởi tạo Django TRƯỚC khi import bất cứ thứ gì đụng đến model
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

from apps.bookings.routing import websocket_urlpatterns  # noqa: E402
from apps.users.ws_auth import JWTAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # Kiểm tra header Origin theo ALLOWED_HOSTS rồi mới xác thực JWT và định tuyến
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddleware(URLRouter(websocket_urlpatterns))
    ),
})

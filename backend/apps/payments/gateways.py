import hashlib
import hmac

from django.conf import settings


def sign(body: bytes) -> str:
    return hmac.new(settings.PAYMENT_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


def verify(body: bytes, signature: str | None) -> bool:
    expected = sign(body).encode()
    # compare_digest: so sánh không phụ thuộc thời gian; encode để header lạ không gây TypeError
    return hmac.compare_digest(expected, (signature or "").encode())
import hashlib
import hmac
import json
import secrets
import urllib.error
import urllib.request
from collections import namedtuple
from urllib.parse import quote_plus, urlencode

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from rest_framework.throttling import SimpleRateThrottle

_HASH_EXCLUDED = {"vnp_SecureHash", "vnp_SecureHashType"}


def client_ip(request) -> str:
    """Cùng cách throttle lấy IP, gồm NUM_PROXIES. SimpleRateThrottle() trần không có scope."""

    class _Ident(SimpleRateThrottle):
        scope = "pay"

        def get_cache_key(self, request, view):
            return None

    return _Ident().get_ident(request)


def sign_vnpay(params: dict[str, str], secret: str) -> str:
    items = sorted(
        (key, value)
        for key, value in params.items()
        if key not in _HASH_EXCLUDED and value not in (None, "")
    )
    data = "&".join(f"{key}={quote_plus(str(value))}" for key, value in items)
    return hmac.new(secret.encode(), data.encode(), hashlib.sha512).hexdigest()


def verify_vnpay(params: dict[str, str], secret: str) -> bool:
    given = params.get("vnp_SecureHash") or ""
    return hmac.compare_digest(sign_vnpay(params, secret), given)


class VNPayGateway:
    @staticmethod
    def checkout_url(payment, ip_addr: str) -> str:
        if not settings.VNPAY_TMN_CODE or not settings.VNPAY_HASH_SECRET:
            raise ImproperlyConfigured("Thiếu VNPAY_TMN_CODE hoặc VNPAY_HASH_SECRET.")
        code = payment.booking.code
        params = {
            "vnp_Version": "2.1.0",
            "vnp_Command": "pay",
            "vnp_TmnCode": settings.VNPAY_TMN_CODE,
            "vnp_Amount": str(payment.amount * 100),
            "vnp_CurrCode": "VND",
            "vnp_TxnRef": payment.txn_ref,
            "vnp_OrderInfo": f"Booking {code}",
            "vnp_OrderType": "other",
            "vnp_Locale": "vn",
            "vnp_ReturnUrl": f"{settings.VNPAY_RETURN_URL.rstrip('/')}/bookings/{code}",
            "vnp_IpAddr": ip_addr or "127.0.0.1",
            "vnp_CreateDate": timezone.localtime(payment.created_at).strftime("%Y%m%d%H%M%S"),
        }
        params["vnp_SecureHash"] = sign_vnpay(params, settings.VNPAY_HASH_SECRET)
        return f"{settings.VNPAY_PAY_URL}?{urlencode(params)}"

    @staticmethod
    def query(payment):
        if not settings.VNPAY_TMN_CODE or not settings.VNPAY_HASH_SECRET:
            raise ImproperlyConfigured("Thiếu VNPAY_TMN_CODE hoặc VNPAY_HASH_SECRET.")
        now = timezone.localtime()
        created = timezone.localtime(payment.created_at)
        fields = {
            "vnp_RequestId": secrets.token_hex(8),
            "vnp_Version": "2.1.0",
            "vnp_Command": "querydr",
            "vnp_TmnCode": settings.VNPAY_TMN_CODE,
            "vnp_TxnRef": payment.txn_ref,
            "vnp_TransactionDate": created.strftime("%Y%m%d%H%M%S"),
            "vnp_CreateDate": now.strftime("%Y%m%d%H%M%S"),
            "vnp_IpAddr": "127.0.0.1",
            "vnp_OrderInfo": f"query {payment.txn_ref}",
        }
        fields["vnp_SecureHash"] = sign_querydr(fields, settings.VNPAY_HASH_SECRET)
        request = urllib.request.Request(
            settings.VNPAY_QUERY_URL,
            data=json.dumps(fields).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status != 200:
                    raise GatewayUnavailable(f"HTTP {response.status}")
                raw = json.loads(response.read().decode())
        except GatewayUnavailable:
            raise
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            raise GatewayUnavailable(str(exc)) from exc
        paid = raw.get("vnp_ResponseCode") == "00" and raw.get("vnp_TransactionStatus") == "00"
        amount = int(raw["vnp_Amount"]) // 100 if paid else None
        return GatewaySnapshot(paid, amount, raw.get("vnp_TransactionNo") or "")


_QUERY_FIELDS = (
    "vnp_RequestId",
    "vnp_Version",
    "vnp_Command",
    "vnp_TmnCode",
    "vnp_TxnRef",
    "vnp_TransactionDate",
    "vnp_CreateDate",
    "vnp_IpAddr",
    "vnp_OrderInfo",
)

GatewaySnapshot = namedtuple("GatewaySnapshot", "paid amount gateway_txn_id")


class GatewayUnavailable(Exception):
    """querydr không trả lời được. Payment giữ nguyên."""


def sign_querydr(fields: dict[str, str], secret: str) -> str:
    data = "|".join(fields[name] for name in _QUERY_FIELDS)
    return hmac.new(secret.encode(), data.encode(), hashlib.sha512).hexdigest()


def sign(body: bytes) -> str:
    return hmac.new(settings.PAYMENT_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


def verify(body: bytes, signature: str | None) -> bool:
    expected = sign(body).encode()
    # compare_digest: so sánh không phụ thuộc thời gian; encode để header lạ không gây TypeError
    return hmac.compare_digest(expected, (signature or "").encode())
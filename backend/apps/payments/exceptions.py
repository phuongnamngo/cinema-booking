from rest_framework import status
from rest_framework.exceptions import APIException


class NoPendingPayment(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Không có giao dịch đang chờ để hủy."
    default_code = "no_pending_payment"


class InvalidSignature(Exception):
    """Chữ ký webhook sai hoặc thiếu."""


class InvalidPayload(Exception):
    """Body webhook không đúng định dạng."""
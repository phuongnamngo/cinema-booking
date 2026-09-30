class InvalidSignature(Exception):
    """Chữ ký webhook sai hoặc thiếu."""


class InvalidPayload(Exception):
    """Body webhook không đúng định dạng."""
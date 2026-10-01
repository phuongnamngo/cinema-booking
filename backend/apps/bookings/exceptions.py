from rest_framework import status
from rest_framework.exceptions import APIException


class SeatUnavailable(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Ghế vừa có người khác chọn, vui lòng chọn ghế khác."
    default_code = "seat_unavailable"

    def __init__(self, labels=None):
        detail = (
            f"Ghế {', '.join(labels)} không còn trống, vui lòng chọn ghế khác."
            if labels
            else None
        )
        super().__init__(detail)


class PendingBookingExists(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "pending_booking_exists"

    def __init__(self, booking_code):
        super().__init__(
            f"Bạn đang giữ ghế cho suất chiếu này (mã {booking_code}). "
            "Hãy hoàn tất hoặc hủy đơn đó trước."
        )


class BookingNotPending(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Chỉ có thể thao tác với đơn đang chờ thanh toán."
    default_code = "booking_not_pending"


class HoldServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Hệ thống giữ ghế tạm thời không khả dụng, vui lòng thử lại."
    default_code = "hold_unavailable"


class TicketRejected(APIException):
    """Vé không thể check-in. `reason` là mã máy đọc được để FE hiển thị đúng thông báo."""

    status_code = status.HTTP_409_CONFLICT
    default_code = "ticket_rejected"

    def __init__(self, reason, message, **extra):
        self.reason = reason
        self.message = message
        # Lưu ý: DRF ép mọi giá trị trong detail thành chuỗi, nên không đưa None vào đây
        super().__init__({"detail": message, "reason": reason, **extra})


class PaymentInProgress(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = (
        "Đơn đang có giao dịch chờ thanh toán nên không thể thay đổi. "
        "Hãy hoàn tất thanh toán hoặc thử lại sau."
    )
    default_code = "payment_in_progress"

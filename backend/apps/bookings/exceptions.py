from rest_framework import status
from rest_framework.exceptions import APIException


class SeatUnavailable(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Ghế vừa có người khác chọn, vui lòng chọn ghế khác."
    default_code = "seat_unavailable"

    def __init__(self, labels=None):
        detail = f"Ghế {', '.join(labels)} không còn trống, vui lòng chọn ghế khác." if labels else None
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
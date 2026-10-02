import math

from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler as drf_exception_handler


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)   # đã gắn sẵn header Retry-After
    if response is not None and isinstance(exc, Throttled):
        message = "Bạn thao tác quá nhanh."
        if exc.wait:
            message += f" Vui lòng thử lại sau {math.ceil(exc.wait)} giây."
        response.data = {"detail": message}   # FE đã hiển thị `detail` sẵn, khỏi sửa gì
    return response
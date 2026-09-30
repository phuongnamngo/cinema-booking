import json
import secrets

from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking
from apps.bookings.services import expire_pending_bookings

from . import gateways, services
from .exceptions import InvalidPayload, InvalidSignature
from .models import Payment
from .serializers import PaymentSerializer


class CreatePaymentView(APIView):
    """POST /bookings/{code}/pay/ - bắt đầu thanh toán cho đơn đang giữ ghế."""

    @extend_schema(request=None, responses={200: PaymentSerializer, 201: PaymentSerializer})
    def post(self, request, code):
        expire_pending_bookings(user=request.user)   # đơn quá hạn thì cập nhật trước khi xét
        booking = get_object_or_404(Booking, code=code, user=request.user)   # của người khác => 404

        payment, created = services.create_payment(booking)
        data = PaymentSerializer(payment, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@extend_schema(exclude=True)
class MockWebhookView(APIView):
    """POST /payments/webhook/mock/ - cổng thanh toán gọi vào (server -> server)."""

    authentication_classes = []           # không dùng JWT: danh tính được chứng minh bằng chữ ký
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            outcome = services.handle_webhook(request.body, request.headers.get("X-Signature"))
        except InvalidSignature:
            return Response({"detail": "Chữ ký không hợp lệ."}, status=status.HTTP_401_UNAUTHORIZED)
        except InvalidPayload as exc:
            return Response(
                {"detail": "Payload không hợp lệ.", "errors": exc.args[0]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"status": outcome})


# --- Cổng thanh toán giả lập (chỉ dùng khi dev) ---

PAGE = """<!doctype html><meta charset="utf-8"><title>Mock Gateway</title>
<body style="font-family:sans-serif;max-width:420px;margin:60px auto">
<h2>Cổng thanh toán giả lập</h2>
<p>Mã giao dịch: <code>{txn_ref}</code></p>
<p>Số tiền: <b>{amount}</b></p>
{content}
</body>"""

FORM = """<form method="post">
<button name="result" value="success">Thanh toán thành công</button>
<button name="result" value="failed">Thanh toán thất bại</button>
</form>"""


@method_decorator(csrf_exempt, name="dispatch")   # mô phỏng một site khác, không có CSRF token của mình
class MockGatewayView(View):
    def dispatch(self, request, *args, **kwargs):
        if not settings.PAYMENT_MOCK_ENABLED:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def _page(self, payment, content):
        amount = f"{payment.amount:,}".replace(",", ".") + "đ"
        return HttpResponse(format_html(PAGE, txn_ref=payment.txn_ref, amount=amount, content=content))

    def get(self, request, txn_ref):
        payment = get_object_or_404(Payment, txn_ref=txn_ref, provider=Payment.Provider.MOCK)
        if payment.status != Payment.Status.PENDING:
            return self._page(payment, format_html("<p>Giao dịch đã xử lý: <b>{}</b></p>", payment.status))
        return self._page(payment, format_html(FORM))

    def post(self, request, txn_ref):
        payment = get_object_or_404(Payment, txn_ref=txn_ref, provider=Payment.Provider.MOCK)
        result = request.POST.get("result")
        if result not in ("success", "failed"):
            return HttpResponseBadRequest("result phải là success hoặc failed")

        # Đóng vai cổng thật: dựng payload, ký, rồi giao cho đúng hàm xử lý webhook.
        # (Qua HTTP thật thì dùng curl ở phần Checkpoint.)
        body = json.dumps({
            "txn_ref": payment.txn_ref,
            "gateway_txn_id": f"MOCK{secrets.token_hex(6).upper()}",
            "amount": payment.amount,
            "result": result,
        }).encode()
        outcome = services.handle_webhook(body, gateways.sign(body))

        return self._page(payment, format_html(
            "<p>Kết quả xử lý: <b>{}</b></p><p>Cổng thật sẽ đưa trình duyệt về trang kết quả "
            "của web. Ở đó React hỏi lại API để biết trạng thái đơn.</p>", outcome,
        ))
import json
import logging
from datetime import timedelta
from functools import partial

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.bookings.exceptions import BookingNotPending
from apps.bookings.models import Booking
from apps.bookings.services import confirm_booking
from apps.bookings.tasks import send_booking_confirmation_email

from . import gateways
from .exceptions import InvalidPayload, InvalidSignature, NoPendingPayment
from .models import Payment
from .serializers import GatewayResultSerializer

logger = logging.getLogger(__name__)


class Outcome:
    CONFIRMED = "confirmed"
    FAILED = "failed"
    DUPLICATE = "duplicate"
    IGNORED = "ignored"
    NEEDS_REVIEW = "needs_review"


def create_payment(booking):
    """Tạo (hoặc dùng lại) giao dịch đang chờ của đơn. Trả về (payment, created)."""
    with transaction.atomic():
        # Khóa booking: trong lúc ta chốt số tiền, không ai đổi được combo/voucher của đơn
        booking = Booking.objects.select_for_update().get(pk=booking.pk)

        if booking.status != Booking.Status.PENDING:
            raise BookingNotPending()
        seconds_left = (booking.expires_at - timezone.now()).total_seconds()
        if seconds_left < settings.PAYMENT_MIN_SECONDS_TO_PAY:
            raise ValidationError(
                {"detail": "Đơn sắp hết hạn giữ ghế, vui lòng chọn lại ghế."}
            )

        existing = Payment.objects.filter(
            booking=booking, status=Payment.Status.PENDING
        ).first()
        if existing:
            return (
                existing,
                False,
            )  # bấm "Thanh toán" nhiều lần vẫn ra cùng một giao dịch

        # Số tiền do SERVER quyết định (đã gồm combo và giảm giá). Unique constraint "một payment
        # pending mỗi đơn" vẫn là chốt chặn cuối ở DB
        return (
            Payment.objects.create(
                booking=booking,
                amount=booking.total_amount,
                provider=settings.PAYMENT_PROVIDER,
            ),
            True,
        )


def cancel_pending_payment(booking):
    """Hủy payment pending. Khóa payment trước booking. Không nhả ghế."""
    with transaction.atomic():
        payment = (
            Payment.objects.select_for_update()
            .filter(booking_id=booking.pk, status=Payment.Status.PENDING)
            .first()
        )
        if payment is None:
            raise NoPendingPayment()
        booking = Booking.objects.select_for_update().get(pk=booking.pk)
        if booking.status != Booking.Status.PENDING or booking.expires_at <= timezone.now():
            raise BookingNotPending()
        payment.status = Payment.Status.CANCELLED
        payment.save(update_fields=["status", "updated_at"])
        return payment


def handle_webhook(raw_body: bytes, signature: str | None) -> str:
    """Xác thực chữ ký, kiểm tra payload rồi xử lý. Trả về một giá trị của Outcome."""
    if not gateways.verify(raw_body, signature):
        raise InvalidSignature()

    try:
        data = json.loads(raw_body)
    except ValueError:
        raise InvalidPayload("JSON không hợp lệ.")

    serializer = GatewayResultSerializer(data=data)
    if not serializer.is_valid():
        raise InvalidPayload(serializer.errors)
    v = serializer.validated_data

    return process_payment_result(
        txn_ref=v["txn_ref"],
        gateway_txn_id=v["gateway_txn_id"],
        amount=v["amount"],
        success=v["result"] == "success",
        payload=data,
    )


def _flag_for_review(payment, reason):
    payment.status = Payment.Status.NEEDS_REVIEW
    payment.failure_reason = reason
    payment.save()
    logger.error("Payment %s cần xử lý thủ công: %s", payment.txn_ref, reason)
    return Outcome.NEEDS_REVIEW


@transaction.atomic
def process_payment_result(
    *, txn_ref, gateway_txn_id, amount, success, payload, failure_reason=None
):
    # Khóa CHỈ dòng payment. Webhook trùng lặp/song song sẽ xếp hàng ở đây
    payment = Payment.objects.select_for_update().filter(txn_ref=txn_ref).first()
    if payment is None:
        logger.warning("Webhook cho giao dịch không tồn tại: %s", txn_ref)
        return Outcome.IGNORED  # trả 200 để cổng ngừng gọi lại
    if payment.status in (Payment.Status.SUCCEEDED, Payment.Status.NEEDS_REVIEW):
        return Outcome.DUPLICATE
    if payment.status in (Payment.Status.CANCELLED, Payment.Status.FAILED):
        if success:
            payment.gateway_txn_id = gateway_txn_id
            payment.raw_payload = payload
            reason = (
                "late_success_after_cancel"
                if payment.status == Payment.Status.CANCELLED
                else "late_success_after_failure"
            )
            return _flag_for_review(payment, reason)
        return Outcome.DUPLICATE
    if payment.status != Payment.Status.PENDING:
        return Outcome.DUPLICATE

    payment.gateway_txn_id = gateway_txn_id
    payment.raw_payload = payload

    if not success:
        payment.status = Payment.Status.FAILED
        payment.failure_reason = failure_reason or "declined_by_gateway"
        payment.save()
        return (
            Outcome.FAILED
        )  # đơn vẫn PENDING, khách có thể thử lại đến khi hết hạn giữ ghế

    if amount != payment.amount:
        return _flag_for_review(
            payment, f"amount_mismatch: expected {payment.amount}, got {amount}"
        )

    # Thứ tự khóa: payment -> booking (không nơi nào khóa ngược lại)
    booking = Booking.objects.select_for_update().get(pk=payment.booking_id)
    if booking.status != Booking.Status.PENDING:
        # Tiền đã thu nhưng đơn đã hết hạn/hủy, ghế có thể đã có người khác mua
        return _flag_for_review(payment, f"booking_{booking.status}")

    if payment.amount != booking.total_amount:
        # Không nên xảy ra (đơn bị khóa sửa khi có giao dịch chờ), nhưng đây là tiền: kiểm tra lại cho chắc
        return _flag_for_review(payment, "booking_total_changed")

    payment.status = Payment.Status.SUCCEEDED
    payment.paid_at = timezone.now()
    payment.save()

    confirm_booking(
        booking
    )  # PENDING -> CONFIRMED, sau commit: nhả Redis + broadcast seats_sold
    transaction.on_commit(
        partial(send_booking_confirmation_email.delay, booking.id), robust=True
    )
    return Outcome.CONFIRMED


def payments_due_for_reconcile(now=None):
    now = now or timezone.now()
    cutoff = now - timedelta(seconds=settings.PAYMENT_RECONCILE_AFTER_SECONDS)
    return Payment.objects.filter(
        provider=Payment.Provider.VNPAY,
        status=Payment.Status.PENDING,
        created_at__lt=cutoff,
    )


def apply_gateway_query(payment):
    try:
        snapshot = gateways.VNPayGateway.query(payment)
    except gateways.GatewayUnavailable:
        logger.exception("Đối soát %s không gọi được cổng", payment.txn_ref)
        return None
    payload = {"source": "querydr"}
    if not snapshot.paid:
        booking = Booking.objects.get(pk=payment.booking_id)
        if booking.status == Booking.Status.PENDING and booking.expires_at > timezone.now():
            return None
        return process_payment_result(
            txn_ref=payment.txn_ref,
            gateway_txn_id=snapshot.gateway_txn_id,
            amount=payment.amount,
            success=False,
            payload=payload,
            failure_reason="not_paid_at_gateway",
        )
    return process_payment_result(
        txn_ref=payment.txn_ref,
        gateway_txn_id=snapshot.gateway_txn_id,
        amount=snapshot.amount,
        success=True,
        payload={**payload, "amount": snapshot.amount},
    )

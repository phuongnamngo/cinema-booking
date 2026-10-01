from django.db import transaction
from django.db.models import F, IntegerField, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.payments.models import Payment
from apps.promotions.exceptions import VoucherNotApplicable
from apps.promotions.models import Combo, Voucher

from .exceptions import BookingNotPending, PaymentInProgress
from .models import Booking, BookingCombo

MAX_COMBO_LINES = 10      # số loại combo khác nhau trong một đơn
MAX_COMBO_QUANTITY = 10   # số phần của mỗi loại
INVALID_VOUCHER = "Mã giảm giá không hợp lệ."


def active_usage_q(now):
    """Đơn đang chiếm một lượt dùng voucher: đã thanh toán, hoặc đang giữ ghế còn hạn.

    Lượt dùng được SUY RA từ trạng thái đơn chứ không lưu bộ đếm: đơn hết hạn/bị hủy thì
    lượt tự được trả, không cần hook nào và không phụ thuộc Celery.
    """
    return Q(status=Booking.Status.CONFIRMED) | Q(status=Booking.Status.PENDING, expires_at__gt=now)


def _lock_editable(booking):
    """Khóa dòng booking và kiểm tra còn sửa được: PENDING, còn hạn, chưa có giao dịch chờ."""
    booking = Booking.objects.select_for_update().get(pk=booking.pk)
    if booking.status != Booking.Status.PENDING or booking.expires_at <= timezone.now():
        raise BookingNotPending()
    if booking.payments.filter(status=Payment.Status.PENDING).exists():
        # Số tiền đã được chốt vào giao dịch: sửa đơn lúc này sẽ làm tiền thu và tổng đơn lệch nhau
        raise PaymentInProgress()
    return booking


def subtotal_parts(booking):
    seats = booking.items.aggregate(
        total=Coalesce(Sum("price"), 0, output_field=IntegerField())
    )["total"]
    combos = booking.combo_lines.aggregate(
        total=Coalesce(
            Sum(F("unit_price") * F("quantity"), output_field=IntegerField()),
            0,
            output_field=IntegerField(),
        )
    )["total"]
    return seats, combos


def recalculate(booking):
    """Nơi DUY NHẤT ghi total_amount/discount_amount. Gọi trong transaction, booking đã bị khóa.

    Raise VoucherNotApplicable nếu tổng mới không còn đủ điều kiện của voucher đang áp.
    """
    seats, combos = subtotal_parts(booking)
    subtotal = seats + combos

    discount = 0
    if booking.voucher_id:
        voucher = booking.voucher
        voucher.check_min_order(subtotal)
        discount = voucher.compute_discount(subtotal)

    booking.discount_amount = discount
    booking.total_amount = subtotal - discount
    booking.save(update_fields=["voucher", "discount_amount", "total_amount", "updated_at"])
    return booking


@transaction.atomic
def set_combos(booking, items):
    """Đặt lại TOÀN BỘ combo của đơn (idempotent). items rỗng = xóa hết combo."""
    booking = _lock_editable(booking)

    wanted = {}   # gộp các dòng trùng combo
    for item in items:
        wanted[item["combo"]] = wanted.get(item["combo"], 0) + item["quantity"]
    if len(wanted) > MAX_COMBO_LINES:
        raise ValidationError({"items": f"Tối đa {MAX_COMBO_LINES} loại combo."})
    if any(qty > MAX_COMBO_QUANTITY for qty in wanted.values()):
        raise ValidationError({"items": f"Tối đa {MAX_COMBO_QUANTITY} phần cho mỗi combo."})

    combos = {c.id: c for c in Combo.objects.filter(id__in=list(wanted), is_active=True)}
    if len(combos) != len(wanted):
        raise ValidationError({"items": "Có combo không tồn tại hoặc đã ngừng bán."})

    booking.combo_lines.all().delete()
    BookingCombo.objects.bulk_create([
        BookingCombo(booking=booking, combo=combos[cid], quantity=qty, unit_price=combos[cid].price)
        for cid, qty in wanted.items()
    ])
    try:
        return recalculate(booking)
    except VoucherNotApplicable:
        # Exception thoát khỏi atomic nên việc xóa/thêm combo ở trên được rollback
        raise ValidationError({
            "items": "Thay đổi này làm đơn không còn đủ điều kiện dùng mã giảm giá. Hãy gỡ mã trước."
        })


@transaction.atomic
def apply_voucher(booking, raw_code):
    booking = _lock_editable(booking)
    code = raw_code.strip().upper()

    # KHÓA DÒNG VOUCHER: mọi người áp cùng một mã xếp hàng ở đây, nên bước đếm lượt bên dưới
    # luôn thấy kết quả đã commit của người đến trước (lượt cuối chỉ thuộc về một người)
    voucher = Voucher.objects.select_for_update().filter(code=code).first()
    if voucher is None or not voucher.is_active:
        raise ValidationError({"code": INVALID_VOUCHER})   # mã sai và mã bị tắt: cùng một thông báo
    if booking.voucher_id == voucher.id:
        return booking   # đã áp mã này rồi: idempotent

    now = timezone.now()
    try:
        voucher.check_usable(now)
        seats, combos = subtotal_parts(booking)
        voucher.check_min_order(seats + combos)
    except VoucherNotApplicable as exc:
        raise ValidationError({"code": str(exc)})

    usage = Booking.objects.filter(voucher=voucher).filter(active_usage_q(now))
    if voucher.usage_limit is not None and usage.count() >= voucher.usage_limit:
        raise ValidationError({"code": "Mã giảm giá đã hết lượt sử dụng."})
    if usage.filter(user_id=booking.user_id).count() >= voucher.per_user_limit:
        raise ValidationError({"code": "Bạn đã dùng hết số lượt cho mã này."})

    booking.voucher = voucher   # đổi sang mã khác thì lượt của mã cũ tự được trả (đếm theo đơn)
    return recalculate(booking)


@transaction.atomic
def remove_voucher(booking):
    booking = _lock_editable(booking)
    if booking.voucher_id is None:
        return booking   # idempotent
    booking.voucher = None
    return recalculate(booking)
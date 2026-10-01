from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Upper

from .exceptions import VoucherNotApplicable


def vnd(amount: int) -> str:
    return f"{amount:,}".replace(",", ".") + "đ"


class Combo(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)
    price = models.PositiveIntegerField()   # VND
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.CheckConstraint(condition=Q(price__gt=0), name="combo_price_positive"),
        ]

    def __str__(self):
        return self.name


class Voucher(models.Model):
    class DiscountType(models.TextChoices):
        PERCENT = "percent", "Phần trăm"
        FIXED = "fixed", "Số tiền cố định"

    code = models.CharField(max_length=32, unique=True)
    description = models.CharField(max_length=255, blank=True)
    discount_type = models.CharField(max_length=10, choices=DiscountType.choices)
    value = models.PositiveIntegerField(help_text="Phần trăm (1-100) hoặc số tiền VND, tùy loại.")
    max_discount = models.PositiveIntegerField(
        null=True, blank=True, help_text="Mức giảm tối đa (chỉ cho loại phần trăm)."
    )
    min_order_amount = models.PositiveIntegerField(default=0)
    usage_limit = models.PositiveIntegerField(
        null=True, blank=True, help_text="Tổng số lượt dùng. Để trống = không giới hạn."
    )
    per_user_limit = models.PositiveSmallIntegerField(default=1)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Mã luôn viết hoa: unique trên cột này đồng nghĩa với "không phân biệt hoa thường"
            models.CheckConstraint(condition=Q(code=Upper("code")), name="voucher_code_uppercase"),
            models.CheckConstraint(
                condition=Q(value__gte=1) & (Q(discount_type="fixed") | Q(value__lte=100)),
                name="voucher_value_range",
            ),
            models.CheckConstraint(
                condition=Q(valid_from__isnull=True)
                | Q(valid_until__isnull=True)
                | Q(valid_until__gt=F("valid_from")),
                name="voucher_valid_window",
            ),
        ]

    def clean(self):
        # Chạy trước khi Django Admin kiểm tra constraint, để gõ "welcome10" vẫn hợp lệ
        self.code = (self.code or "").strip().upper()

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code

    # --- Quy tắc nghiệp vụ (thuần, không đụng DB) ---

    def check_usable(self, now):
        """Quy tắc về thời gian và trạng thái. Chỉ kiểm tra lúc ÁP MÃ."""
        if not self.is_active:
            raise VoucherNotApplicable("Mã giảm giá không hợp lệ.")
        if self.valid_from and now < self.valid_from:
            raise VoucherNotApplicable("Mã giảm giá chưa đến thời gian áp dụng.")
        if self.valid_until and now > self.valid_until:
            raise VoucherNotApplicable("Mã giảm giá đã hết hạn.")

    def check_min_order(self, subtotal):
        """Kiểm tra lúc áp mã VÀ mỗi khi tổng tiền đổi (thêm/bớt combo)."""
        if subtotal < self.min_order_amount:
            raise VoucherNotApplicable(
                f"Đơn hàng cần tối thiểu {vnd(self.min_order_amount)} để dùng mã này."
            )

    def compute_discount(self, subtotal):
        if self.discount_type == self.DiscountType.PERCENT:
            raw = subtotal * self.value // 100   # chia nguyên: làm tròn xuống
            if self.max_discount is not None:
                raw = min(raw, self.max_discount)
        else:
            raw = self.value
        # Không bao giờ giảm quá tay: đơn luôn còn ít nhất MIN_PAYABLE_AMOUNT
        ceiling = max(0, subtotal - settings.MIN_PAYABLE_AMOUNT)
        return min(raw, ceiling)
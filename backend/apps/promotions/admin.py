from django.contrib import admin
from django.db.models import Count, Q

from .models import Combo, Voucher


@admin.register(Combo)
class ComboAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    list_filter = ("is_active",)


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = (
        "code", "discount_type", "value", "min_order_amount",
        "usage_limit", "in_use", "valid_until", "is_active",
    )
    list_filter = ("is_active", "discount_type")
    search_fields = ("code",)

    def get_queryset(self, request):
        live = Q(bookings__status__in=["pending", "confirmed"])
        return super().get_queryset(request).annotate(_in_use=Count("bookings", filter=live))

    @admin.display(description="Đơn đang giữ/đã thanh toán", ordering="_in_use")
    def in_use(self, obj):
        return obj._in_use
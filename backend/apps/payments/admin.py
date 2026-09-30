from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("txn_ref", "booking", "provider", "amount", "status", "paid_at", "created_at")
    list_filter = ("status", "provider")
    search_fields = ("txn_ref", "gateway_txn_id", "booking__code")
    list_select_related = ("booking",)
    readonly_fields = [f.name for f in Payment._meta.fields]   # dữ liệu tiền: chỉ xem, không sửa tay

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
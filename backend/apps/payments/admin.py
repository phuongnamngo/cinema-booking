from django.contrib import admin
from django.utils import timezone

from .models import Payment


class UnreviewedPaymentFilter(admin.SimpleListFilter):
    title = "hàng đợi"
    parameter_name = "review"

    def lookups(self, request, model_admin):
        return (("unreviewed", "Chưa ghi nhận"),)

    def queryset(self, request, queryset):
        if self.value() == "unreviewed":
            return queryset.filter(
                status=Payment.Status.NEEDS_REVIEW, reviewed_at__isnull=True
            )
        return queryset


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("txn_ref", "booking", "provider", "amount", "status", "paid_at", "created_at")
    list_filter = (UnreviewedPaymentFilter, "status", "provider")
    search_fields = ("txn_ref", "gateway_txn_id", "booking__code")
    list_select_related = ("booking",)
    actions = None

    def get_readonly_fields(self, request, obj=None):
        fields = [field.name for field in Payment._meta.fields]
        if obj is not None and obj.status == Payment.Status.NEEDS_REVIEW:
            fields = [name for name in fields if name != "review_note"]
        return fields

    def save_model(self, request, obj, form, change):
        if (
            change
            and obj.status == Payment.Status.NEEDS_REVIEW
            and (obj.review_note or "").strip()
            and obj.reviewed_at is None
        ):
            obj.reviewed_at = timezone.now()
            obj.reviewed_by = request.user
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
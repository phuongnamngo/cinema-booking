from django.contrib import admin

from .models import Booking, BookingSeat, BookingCombo


class BookingSeatInline(admin.TabularInline):
    model = BookingSeat
    extra = 0
    can_delete = False
    readonly_fields = ("showtime", "seat", "price", "is_active")

    def has_add_permission(self, request, obj=None):
        return False


class BookingComboInline(admin.TabularInline):
    model = BookingCombo
    extra = 0
    can_delete = False
    readonly_fields = ("combo", "quantity", "unit_price")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "user",
        "showtime",
        "status",
        "total_amount",
        "expires_at",
        "checked_in_at",
    )
    list_filter = ("status",)
    search_fields = ("code", "user__email")
    list_select_related = ("user", "showtime__movie", "showtime__room")
    # Không cho sửa tay: đổi trạng thái phải qua services để cờ is_active luôn đồng bộ
    readonly_fields = (
        "code",
        "user",
        "showtime",
        "status",
        "total_amount",
        "expires_at",
        "checked_in_at",
        "checked_in_by",
        "voucher",
        "discount_amount",
    )
    inlines = [BookingSeatInline, BookingComboInline]

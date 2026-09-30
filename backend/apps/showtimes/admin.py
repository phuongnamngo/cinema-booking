from django.contrib import admin

from .models import Showtime


@admin.register(Showtime)
class ShowtimeAdmin(admin.ModelAdmin):
    list_display = ("movie", "room", "start_time", "end_time", "price_standard", "is_active")
    list_filter = ("is_active", "room__cinema")
    list_select_related = ("movie", "room__cinema")
    readonly_fields = ("end_time",)
    date_hierarchy = "start_time"
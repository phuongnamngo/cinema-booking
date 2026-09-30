from django.contrib import admin

from .models import Cinema, Room, Seat


@admin.register(Cinema)
class CinemaAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "is_active")
    list_filter = ("city", "is_active")
    search_fields = ("name", "address")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "cinema", "is_active")
    list_filter = ("cinema",)
    list_select_related = ("cinema",)   # tránh N+1: __str__ của Room truy cập cinema.name


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("room", "row", "number", "seat_type")
    list_filter = ("seat_type", "room")
    list_select_related = ("room__cinema",)
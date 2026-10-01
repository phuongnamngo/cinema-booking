from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User


# Register your models here.
@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("username", "email", "phone")

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Cinema", {"fields": ("phone", "role", "cinema")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Cinema", {"fields": ("email", "phone", "role", "cinema")}),
    )

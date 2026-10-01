from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import User


def is_admin(user) -> bool:
    return bool(user and user.is_authenticated and user.role == User.Role.ADMIN)


def is_staff_member(user) -> bool:
    """Nhân viên rạp hoặc admin. (Khác với user.is_staff của Django: cờ đó chỉ nghĩa là vào được /admin)"""
    return bool(
        user
        and user.is_authenticated
        and user.role in (User.Role.STAFF, User.Role.ADMIN)
    )


class IsAdminOrReadOnly(BasePermission):
    """Ai cũng được xem (GET/HEAD/OPTIONS). Chỉ role admin được ghi."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return is_admin(request.user)


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_admin(request.user)


class IsStaffOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_staff_member(request.user)

from rest_framework.permissions import SAFE_METHODS, BasePermission
from .models import User


def is_admin(user) -> bool:
    return bool(user and user.is_authenticated and user.role == User.Role.ADMIN)


class IsAdminOrReadOnly(BasePermission):
    """Ai cũng được xem (GET/HEAD/OPTIONS). Chỉ role admin được ghi."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return is_admin(request.user)

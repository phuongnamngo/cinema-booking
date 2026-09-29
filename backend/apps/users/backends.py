from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Cho phep dang nhap bang email va username"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        User = get_user_model()
        feild = "email__iexact" if "@" in username else "username"
        try:
            user = User.objects.get(**{feild: username})
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

from django.db import transaction
from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import (
    CinemaTokenObtainPairSerializer,
    RegisterSerializer,
    UserSerializer,
)

from .tasks import send_welcome_email


# Create your views here.
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        # Sau khi commit; robust=True: broker lỗi thì chỉ ghi log, đăng ký vẫn thành công
        transaction.on_commit(lambda: send_welcome_email.delay(user.id), robust=True)


class LoginView(TokenObtainPairView):
    serializer_class = CinemaTokenObtainPairSerializer


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

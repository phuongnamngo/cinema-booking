from rest_framework import viewsets

from apps.users.permissions import IsAdminOrReadOnly, is_admin

from .models import Combo
from .serializers import ComboSerializer


class ComboViewSet(viewsets.ModelViewSet):
    serializer_class = ComboSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None   # danh sách ngắn, trả hết một lần
    # Không DELETE: combo đã nằm trong đơn cũ (PROTECT). Ngừng bán bằng is_active=false
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        qs = Combo.objects.all()
        return qs if is_admin(self.request.user) else qs.filter(is_active=True)
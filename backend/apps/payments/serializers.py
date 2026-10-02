from django.urls import reverse
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from .gateways import VNPayGateway, client_ip
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    booking_code = serializers.CharField(source="booking.code", read_only=True)
    expires_at = serializers.DateTimeField(source="booking.expires_at", read_only=True)
    payment_url = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ("txn_ref", "booking_code", "amount", "status", "payment_url", "expires_at")
        read_only_fields = fields

    @extend_schema_field(str)
    def get_payment_url(self, payment):
        if payment.status != Payment.Status.PENDING:
            return None
        if payment.provider == Payment.Provider.VNPAY:
            ip_addr = client_ip(self.context["request"])
            return VNPayGateway.checkout_url(payment, ip_addr)
        if payment.provider != Payment.Provider.MOCK:
            return None
        path = reverse("mock-gateway", args=[payment.txn_ref])
        return self.context["request"].build_absolute_uri(path)


class GatewayResultSerializer(serializers.Serializer):
    """Định dạng webhook của cổng mock."""

    txn_ref = serializers.CharField(max_length=64)
    gateway_txn_id = serializers.CharField(max_length=64)
    amount = serializers.IntegerField(min_value=0)
    result = serializers.ChoiceField(choices=["success", "failed"])
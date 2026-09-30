from django.urls import path

from .views import CreatePaymentView, MockWebhookView

urlpatterns = [
    path("bookings/<str:code>/pay/", CreatePaymentView.as_view(), name="booking-pay"),
    path("payments/webhook/mock/", MockWebhookView.as_view(), name="payment-webhook-mock"),
]
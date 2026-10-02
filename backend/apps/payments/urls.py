from django.urls import path

from .views import CancelPaymentView, CreatePaymentView, MockWebhookView, VNPayIPNView

urlpatterns = [
    path("bookings/<str:code>/pay/", CreatePaymentView.as_view(), name="booking-pay"),
    path(
        "bookings/<str:code>/payments/cancel/",
        CancelPaymentView.as_view(),
        name="booking-cancel-payment",
    ),
    path("payments/webhook/mock/", MockWebhookView.as_view(), name="payment-webhook-mock"),
    path("payments/webhook/vnpay/", VNPayIPNView.as_view(), name="payment-webhook-vnpay"),
]
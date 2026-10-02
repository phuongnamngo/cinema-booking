from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.core.testing import rates

from .test_checkout import CheckoutMixin, make_booking


class BookingThrottleTests(CheckoutMixin, APITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.addCleanup(cache.clear)

    def test_voucher_attempts_are_limited_per_user_and_only_on_that_endpoint(self):
        bob_booking = make_booking(self.bob, self.showtime, [self.a2])
        with rates(voucher="3/min"):
            alice = [self.put_voucher("NOPE").status_code for _ in range(4)]
            bob = self.put_voucher("NOPE", booking=bob_booking, user=self.bob).status_code
            combos = self.put_combos((self.popcorn, 1)).status_code   # scope khác: không bị ảnh hưởng
        self.assertEqual(alice, [400, 400, 400, 429])
        self.assertEqual(bob, 400)   # mỗi người một bộ đếm
        self.assertEqual(combos, 200)

    def test_hold_attempts_are_limited_per_user(self):
        url = reverse("showtime-hold", args=[self.showtime.id])
        self.client.force_authenticate(self.alice)
        with rates(hold="2/min"):
            codes = [self.client.post(url, {"seat_ids": []}, format="json").status_code for _ in range(3)]
        self.assertEqual(codes, [400, 400, 429])

    def test_payment_creation_is_limited_per_user(self):
        self.client.force_authenticate(self.alice)
        url = self.url("booking-pay")
        with rates(pay="2/min"):
            codes = [self.client.post(url).status_code for _ in range(3)]
        self.assertEqual(codes, [201, 200, 429])
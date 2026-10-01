from django.core.management.base import BaseCommand

from apps.promotions.models import Combo, Voucher

COMBOS = [
    ("Combo 1 (Bắp + Nước)", "1 bắp ngọt lớn + 1 nước ngọt", 79000),
    ("Combo đôi", "1 bắp lớn + 2 nước ngọt", 109000),
    ("Nước ngọt", "1 ly nước ngọt", 29000),
    ("Bắp ngọt", "1 bắp ngọt vừa", 49000),
]

VOUCHERS = [
    {
        "code": "WELCOME10",
        "description": "Giảm 10% (tối đa 30.000đ) cho đơn từ 100.000đ",
        "discount_type": "percent",
        "value": 10,
        "max_discount": 30000,
        "min_order_amount": 100000,
        "per_user_limit": 1,
    },
    {
        "code": "SAVE20K",
        "description": "Giảm 20.000đ cho đơn từ 150.000đ",
        "discount_type": "fixed",
        "value": 20000,
        "min_order_amount": 150000,
        "usage_limit": 100,
        "per_user_limit": 2,
    },
    {
        "code": "FLASH50",
        "description": "Giảm 50% (tối đa 50.000đ), chỉ 2 lượt đầu tiên",
        "discount_type": "percent",
        "value": 50,
        "max_discount": 50000,
        "min_order_amount": 100000,
        "usage_limit": 2,
        "per_user_limit": 1,
    },
]


class Command(BaseCommand):
    help = "Tạo combo bắp nước và các mã giảm giá demo (chạy lại nhiều lần vẫn an toàn)"

    def handle(self, *args, **options):
        for order, (name, description, price) in enumerate(COMBOS, start=1):
            Combo.objects.update_or_create(
                name=name,
                defaults={
                    "description": description,
                    "price": price,
                    "sort_order": order,
                    "is_active": True,
                },
            )
        for data in VOUCHERS:
            defaults = {k: v for k, v in data.items() if k != "code"}
            Voucher.objects.update_or_create(code=data["code"], defaults=defaults)
        self.stdout.write(
            self.style.SUCCESS(
                f"Xong. {len(COMBOS)} combo, {len(VOUCHERS)} voucher: "
                + ", ".join(v["code"] for v in VOUCHERS)
            )
        )

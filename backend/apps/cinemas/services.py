import string

from django.db import transaction

from .models import Seat


@transaction.atomic
def generate_seats(room, rows, seats_per_row, vip_rows=(), couple_rows=()):
    """Sinh sơ đồ ghế cho phòng: hàng A, B, C... mỗi hàng `seats_per_row` ghế."""
    labels = string.ascii_uppercase[:rows]
    vip, couple = set(vip_rows), set(couple_rows)

    seats = []
    for row in labels:
        if row in couple:
            seat_type = Seat.SeatType.COUPLE
        elif row in vip:
            seat_type = Seat.SeatType.VIP
        else:
            seat_type = Seat.SeatType.STANDARD
        for number in range(1, seats_per_row + 1):
            seats.append(Seat(room=room, row=row, number=number, seat_type=seat_type))

    return Seat.objects.bulk_create(seats)   # 1 query INSERT thay vì N query
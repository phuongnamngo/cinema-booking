from django.utils import timezone

from .models import Booking, BookingSeat


def bookings_with_details():
    return Booking.objects.select_related(
        "voucher", "showtime__movie", "showtime__room__cinema"
    ).prefetch_related("items__seat", "combo_lines__combo", "payments")


def get_seat_states(showtime, user=None):
    """Trả về {seat_id: 'held' | 'mine' | 'sold'}. Ghế không có trong dict là 'available'."""
    uid = user.id if user is not None and user.is_authenticated else None
    now = timezone.now()
    rows = BookingSeat.objects.filter(showtime=showtime, is_active=True).values_list(
        "seat_id", "booking__status", "booking__expires_at", "booking__user_id"
    )
    states = {}
    for seat_id, status, expires_at, owner_id in rows:
        if status == Booking.Status.CONFIRMED:
            states[seat_id] = "sold"
        elif status == Booking.Status.PENDING and expires_at > now:
            states[seat_id] = "mine" if owner_id == uid else "held"
    return states

from datetime import datetime, time, timedelta

from django.db.models import Count, F, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from apps.bookings.models import Booking, BookingSeat
from apps.cinemas.models import Seat
from apps.payments.models import Payment
from apps.showtimes.models import Showtime


def day_bounds(date_from, date_to):
    """[00:00 của date_from, 00:00 của ngày sau date_to) theo giờ Việt Nam (aware datetime)."""
    start = timezone.make_aware(datetime.combine(date_from, time.min))
    end = timezone.make_aware(datetime.combine(date_to + timedelta(days=1), time.min))
    return start, end


def revenue_report(date_from, date_to):
    """Doanh thu theo NGÀY THANH TOÁN (giờ Việt Nam). Chỉ tính payment thành công."""
    start, end = day_bounds(date_from, date_to)
    rows = (
        Payment.objects.filter(
            status=Payment.Status.SUCCEEDED, paid_at__gte=start, paid_at__lt=end
        )
        # TruncDate tính ngày theo giờ VN ngay trong SQL; nếu nhóm theo UTC thì giao dịch
        # lúc 00:30 sáng sẽ bị xếp vào ngày hôm trước
        .annotate(day=TruncDate("paid_at", tzinfo=timezone.get_current_timezone()))
        .values("day")
        .annotate(revenue=Sum("amount"), orders=Count("id"))
        .order_by("day")   # luôn khai báo rõ ràng, không dựa vào Meta.ordering
    )
    by_day = {row["day"]: row for row in rows}

    days, current = [], date_from
    while current <= date_to:   # bù những ngày không có giao dịch để biểu đồ liền mạch
        row = by_day.get(current)
        days.append({
            "date": current,
            "revenue": row["revenue"] if row else 0,
            "orders": row["orders"] if row else 0,
        })
        current += timedelta(days=1)

    return {
        "date_from": date_from,
        "date_to": date_to,
        "total_revenue": sum(d["revenue"] for d in days),
        "total_orders": sum(d["orders"] for d in days),
        "days": days,
    }


def top_movies(date_from, date_to, limit):
    """Phim bán chạy theo NGÀY CHIẾU. Chỉ tính vé của đơn đã xác nhận."""
    start, end = day_bounds(date_from, date_to)
    rows = (
        BookingSeat.objects.filter(
            booking__status=Booking.Status.CONFIRMED,
            showtime__start_time__gte=start,
            showtime__start_time__lt=end,
        )
        # Chỉ đi qua các FK (nhiều-một) nên không bị nhân dòng
        .values(movie_id=F("showtime__movie_id"), title=F("showtime__movie__title"))
        .annotate(tickets=Count("id"), revenue=Sum("price"))
        .order_by("-tickets", "title")[:limit]
    )
    return {"date_from": date_from, "date_to": date_to, "movies": list(rows)}


def showtime_occupancy(date_from, date_to):
    """Tỉ lệ lấp đầy từng suất chiếu trong khoảng ngày (theo ngày chiếu)."""
    start, end = day_bounds(date_from, date_to)

    # Hai Subquery thay vì JOIN trực tiếp: JOIN cả ghế của phòng lẫn vé đã bán sẽ nhân dòng
    # lên (số ghế x số vé) và làm sai cả hai con số
    sold = (
        BookingSeat.objects.filter(
            showtime=OuterRef("pk"), booking__status=Booking.Status.CONFIRMED
        )
        .order_by()
        .values("showtime")
        .annotate(c=Count("id"))
        .values("c")
    )
    total = (
        Seat.objects.filter(room=OuterRef("room_id"))
        .order_by()
        .values("room")
        .annotate(c=Count("id"))
        .values("c")
    )

    showtimes = (
        Showtime.objects.filter(is_active=True, start_time__gte=start, start_time__lt=end)
        .select_related("movie", "room__cinema")
        .annotate(
            seats_total=Coalesce(Subquery(total), Value(0)),
            seats_sold=Coalesce(Subquery(sold), Value(0)),
        )
        .order_by("start_time", "id")
    )

    rows, sum_total, sum_sold = [], 0, 0
    for s in showtimes:
        sum_total += s.seats_total
        sum_sold += s.seats_sold
        rows.append({
            "showtime_id": s.id,
            "movie_title": s.movie.title,
            "cinema_name": s.room.cinema.name,
            "room_name": s.room.name,
            "start_time": s.start_time,
            "seats_total": s.seats_total,
            "seats_sold": s.seats_sold,
            "occupancy": round(s.seats_sold / s.seats_total, 4) if s.seats_total else 0.0,
        })

    return {
        "date_from": date_from,
        "date_to": date_to,
        "overall_occupancy": round(sum_sold / sum_total, 4) if sum_total else 0.0,
        "showtimes": rows,
    }
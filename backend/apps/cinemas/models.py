from django.db import models


class Cinema(models.Model):
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Room(models.Model):
    cinema = models.ForeignKey(Cinema, on_delete=models.PROTECT, related_name="rooms")
    name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["cinema_id", "name"]
        constraints = [
            models.UniqueConstraint(fields=["cinema", "name"], name="uniq_room_name_per_cinema"),
        ]

    def __str__(self):
        return f"{self.cinema.name} - {self.name}"


class Seat(models.Model):
    class SeatType(models.TextChoices):
        STANDARD = "standard", "Thường"
        VIP = "vip", "VIP"
        COUPLE = "couple", "Đôi"

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="seats")
    row = models.CharField(max_length=2)              # "A", "B", ...
    number = models.PositiveSmallIntegerField()       # 1, 2, 3, ...
    seat_type = models.CharField(max_length=20, choices=SeatType.choices, default=SeatType.STANDARD)

    class Meta:
        ordering = ["row", "number"]
        constraints = [
            models.UniqueConstraint(fields=["room", "row", "number"], name="uniq_seat_position_per_room"),
        ]

    @property
    def label(self):
        return f"{self.row}{self.number}"

    def __str__(self):
        return f"{self.room_id}:{self.label}"
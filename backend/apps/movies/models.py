from django.db import models
from django.core.validators import MinValueValidator

# Create your models here.


class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Movie(models.Model):
    class Status(models.TextChoices):
        COMING_SOON = "coming_soon", "Sắp chiếu"
        NOW_SHOWING = "now_showing", "Đang chiếu"
        ENDED = "ended", "Ngừng chiếu"

    class AgeRating(models.TextChoices):
        P = "P", "P - Mọi lứa tuổi"
        K = "K", "K - Dưới 13 tuổi (có người giám hộ)"
        T13 = "T13", "T13 - 13+"
        T16 = "T16", "T16 - 16+"
        T18 = "T18", "T18 - 18+"

    title = models.CharField(max_length=255)
    synopsis = models.TextField(blank=True)
    duration_minutes = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)]
    )
    release_date = models.DateField()
    poster_url = models.URLField(blank=True)
    trailer_url = models.URLField(blank=True)
    age_rating = models.CharField(
        max_length=5, choices=AgeRating.choices, default=AgeRating.P
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.COMING_SOON
    )
    genres = models.ManyToManyField(Genre, related_name="movies", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-release_date", "title"]
        indexes = [models.Index(fields=["status", "release_date"])]

    def __str__(self):
        return self.title

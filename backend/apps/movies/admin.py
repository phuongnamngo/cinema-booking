from django.contrib import admin

from .models import Genre, Movie


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "age_rating", "release_date", "duration_minutes")
    list_filter = ("status", "age_rating", "genres")
    search_fields = ("title",)
    filter_horizontal = ("genres",)
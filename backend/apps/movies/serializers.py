from rest_framework import serializers

from .models import Genre, Movie


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ("id", "name")


class MovieSerializer(serializers.ModelSerializer):
    # Đọc: trả object đầy đủ. Ghi: nhận danh sách id
    genres = GenreSerializer(many=True, read_only=True)
    genre_ids = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.all(),
        many=True,
        write_only=True,
        source="genres",
        required=False,
    )

    class Meta:
        model = Movie
        fields = (
            "id", "title", "synopsis", "duration_minutes", "release_date",
            "poster_url", "trailer_url", "age_rating", "status",
            "genres", "genre_ids", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
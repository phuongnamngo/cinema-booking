from rest_framework import serializers

from .models import Combo


class ComboSerializer(serializers.ModelSerializer):
    class Meta:
        model = Combo
        fields = ("id", "name", "description", "price", "is_active", "sort_order")
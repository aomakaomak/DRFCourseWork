from rest_framework import serializers

from .models import Habit
from .validators import validate_habit_business_rules


class HabitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Habit
        fields = (
            "id",
            "user",
            "place",
            "time",
            "action",
            "is_pleasant",
            "related_habit",
            "periodicity",
            "reward",
            "time_to_complete",
            "is_public",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at")

    def validate(self, attrs):
        """
        Общая валидация с применением всех бизнес-правил.
        """
        validate_habit_business_rules(attrs, instance=self.instance)
        return attrs

    def create(self, validated_data):
        """
        Пользователь берётся из request.user, чтобы нельзя было создать
        привычку от имени другого пользователя.
        """
        request = self.context.get("request")
        if request is not None and request.user and not request.user.is_anonymous:
            validated_data["user"] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        На всякий случай не даём поменять пользователя через PATCH/PUT.
        """
        validated_data.pop("user", None)
        return super().update(instance, validated_data)

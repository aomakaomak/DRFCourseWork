from typing import Optional

from rest_framework.serializers import ValidationError

from .models import Habit


def validate_habit_business_rules(
    attrs: dict, instance: Optional[Habit] = None
) -> None:
    """
    Комплексный валидатор бизнес-правил для модели Habit.

    Правила из ТЗ:
    1. Исключить одновременный выбор связанной привычки и указания вознаграждения.
       -> reward и related_habit взаимоисключающие.

    2. Время выполнения должно быть не больше 120 секунд.
       (дополнительно к валидатору поля; здесь для подстраховки при partial update).

    3. В связанные привычки могут попадать только привычки с признаком приятной привычки.
       -> related_habit.is_pleasant must be True.

    4. У приятной привычки не может быть вознаграждения или связанной привычки.
       -> если is_pleasant = True, то reward is None/"" и related_habit is None.

    5. Нельзя выполнять привычку реже, чем 1 раз в 7 дней.
       -> periodicity в диапазоне [1, 7]. (поле уже ограничено валидаторами модели,
          но проверим и здесь, чтобы сработало и в partial update).
    """

    errors = {}

    # Берём значения с учётом instance (важно для partial update)
    def get_value(field_name: str):
        if field_name in attrs:
            return attrs[field_name]
        if instance is not None:
            return getattr(instance, field_name)
        return None

    is_pleasant = get_value("is_pleasant")
    reward = get_value("reward")
    related_habit = get_value("related_habit")
    periodicity = get_value("periodicity")
    time_to_complete = get_value("time_to_complete")

    # 1. reward и related_habit взаимоисключающие
    if reward and related_habit:
        errors["reward"] = (
            "Нельзя одновременно указывать вознаграждение и связанную привычку."
        )
        errors["related_habit"] = (
            "Нельзя одновременно указывать связанную привычку и вознаграждение."
        )

    # 2. Время выполнения <= 120 (дополнительная защита)
    if time_to_complete is not None and time_to_complete > 120:
        errors["time_to_complete"] = (
            "Время на выполнение привычки не может превышать 120 секунд."
        )

    # 3. В связанные привычки могут попадать только приятные привычки
    if related_habit is not None and not related_habit.is_pleasant:
        errors["related_habit"] = (
            "В связанные привычки могут попадать только приятные привычки."
        )

    # 4. У приятной привычки не может быть вознаграждения или связанной привычки
    if is_pleasant:
        if reward:
            errors["reward"] = "У приятной привычки не может быть вознаграждения."
        if related_habit is not None:
            errors["related_habit"] = (
                "У приятной привычки не может быть связанной привычки."
            )

    # 5. Нельзя выполнять привычку реже, чем 1 раз в 7 дней (periodicity ∈ [1, 7])
    if periodicity is not None:
        try:
            value = int(periodicity)
        except (TypeError, ValueError):
            errors["periodicity"] = "Периодичность должна быть целым числом от 1 до 7."
        else:
            if value < 1 or value > 7:
                errors["periodicity"] = (
                    "Нельзя выполнять привычку реже, чем 1 раз в 7 дней."
                )

    if errors:
        # DRF ValidationError: поддерживает ошибки по полям
        raise ValidationError(errors)

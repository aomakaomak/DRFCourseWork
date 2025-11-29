from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Habit(models.Model):
    """
    Модель пользовательской привычки.

    is_pleasant = False -> полезная привычка
    is_pleasant = True  -> приятная привычка (используется как награда)
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="habits",
        verbose_name="Пользователь",
        help_text="Пользователь, создавший привычку.",
    )

    place = models.CharField(
        max_length=255,
        verbose_name="Место",
        help_text="Место, в котором необходимо выполнять привычку.",
    )

    time = models.TimeField(
        verbose_name="Время",
        help_text="Время, когда необходимо выполнять привычку.",
    )

    action = models.CharField(
        max_length=255,
        verbose_name="Действие",
        help_text="Формулировка действия, которое представляет собой привычка.",
    )

    is_pleasant = models.BooleanField(
        default=False,
        verbose_name="Приятная привычка",
        help_text="Отметьте, если привычка является приятной (вознаграждение), а не полезной.",
    )

    related_habit = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reward_for",
        verbose_name="Связанная привычка",
        help_text="Приятная привычка, которая выполняется как вознаграждение за эту полезную привычку.",
    )

    periodicity = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(1, message="Нельзя выполнять привычку реже, чем 1 раз в 7 дней."),
            MaxValueValidator(7, message="Нельзя выполнять привычку реже, чем 1 раз в 7 дней."),
        ],
        verbose_name="Периодичность (дни)",
        help_text="Периодичность выполнения привычки в днях. От 1 до 7.",
    )

    reward = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Вознаграждение",
        help_text="Чем вы вознаграждаете себя после выполнения привычки.",
    )

    time_to_complete = models.PositiveSmallIntegerField(
        validators=[
            MaxValueValidator(120, message="Время на выполнение привычки не может превышать 120 секунд."),
        ],
        verbose_name="Время на выполнение (секунды)",
        help_text="Предполагаемое время на выполнение привычки в секундах (не более 120).",
    )

    is_public = models.BooleanField(
        default=False,
        verbose_name="Публичная привычка",
        help_text="Если отмечено, привычка доступна другим пользователям как пример.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создана",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Обновлена",
    )

    class Meta:
        verbose_name = "Привычка"
        verbose_name_plural = "Привычки"
        ordering = ("time", "place")

    def __str__(self) -> str:
        habit_type = "приятная" if self.is_pleasant else "полезная"
        return f"{self.user} — {habit_type} привычка: {self.action}"


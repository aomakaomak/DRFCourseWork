from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    telegram_chat_id = models.BigIntegerField(
        null=True,
        blank=True,
        unique=True,
        verbose_name="Telegram chat id",
        help_text="ID чата пользователя в Telegram для отправки уведомлений.",
    )

    def __str__(self):
        return self.username

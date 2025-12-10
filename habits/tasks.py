import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Habit


@shared_task
def send_habit_reminders():
    """
    Периодическая задача для отправки напоминаний по привычкам.

    Логика простая:
    - Берём текущее локальное время.
    - Ищем привычки с таким же часом и минутой.
    - Проверяем periodicity: ((сегодня - дата создания) % periodicity == 0).
    - Для каждого пользователя с telegram_chat_id отправляем сообщение в Telegram.
    """
    now = timezone.localtime()
    today = now.date()

    # Фильтруем по времени
    habits = Habit.objects.filter(
        time__hour=now.hour,
        time__minute=now.minute,
    )

    for habit in habits:
        # Проверка периодичности
        days_diff = (today - habit.created_at.date()).days
        if days_diff < 0:
            continue
        if days_diff % habit.periodicity != 0:
            continue

        user = habit.user
        chat_id = getattr(user, "telegram_chat_id", None)
        if not chat_id:
            continue

        text = (
            f"Напоминание о привычке:\n"
            f"{habit.action}\n"
            f"Место: {habit.place}\n"
            f"Время: {habit.time.strftime('%H:%M')}"
        )

        url = (
            f"{settings.TELEGRAM_API_URL}/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        )

        try:
            requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=5)
        except requests.RequestException:
            continue

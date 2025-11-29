import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")  # имя проекта подставь своё

app = Celery("config")

# Берём настройки CELERY_* из Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автоматически искать tasks.py во всех приложениях
app.autodiscover_tasks()

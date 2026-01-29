# Habits Tracker (Django + DRF)

Сервис для ведения пользовательских привычек с поддержкой полезных и приятных привычек (приятные могут выступать наградой).  
Проект построен на Django и Django REST Framework. Для фоновых задач используется связка Celery + Redis (наличие сервисов и контейнера celery видно в составе проекта).

---

## Возможности

- Регистрация и аутентификация пользователей.
- Создание, просмотр, редактирование и удаление привычек.
- Разделение привычек на:
  - **полезные** (`is_pleasant = False`);
  - **приятные** (`is_pleasant = True`) — могут использоваться как награда.
- Возможность указать:
  - место и время выполнения;
  - периодичность выполнения;
  - награду текстом **или** связанную приятную привычку как вознаграждение;
  - публичность привычки (доступна другим пользователям как пример).
- Валидации бизнес-правил на уровне модели/сериализаторов (в зависимости от реализации проекта).

---

## Модель Habit

Модель пользовательской привычки:

- `user` — владелец привычки.
- `place` — место выполнения.
- `time` — время выполнения.
- `action` — формулировка действия.
- `is_pleasant` — признак приятной привычки.
- `related_habit` — ссылка на приятную привычку-вознаграждение.
- `periodicity` — периодичность в днях, допустимый диапазон 1–7.
- `reward` — текстовое вознаграждение.
- `time_to_complete` — время на выполнение, максимум 120 секунд.
- `is_public` — публичная привычка.
- `created_at`, `updated_at` — служебные метки времени.

Логика по смыслу модели:

- **Полезная** привычка может иметь вознаграждение:
  - либо через поле `reward`,
  - либо через `related_habit` (приятная привычка).
- **Приятная** привычка, как правило, не должна ссылаться на `related_habit` и не нуждается в `reward` (эти ограничения обычно реализуют на уровне сериализаторов/валидаторов).

---

## Технологии

- Python 3.11+ (в проекте может использоваться 3.13 по локальной конфигурации).
- Django
- Django REST Framework
- PostgreSQL
- Celery
- Redis
- Nginx (как обратный прокси в docker-окружении)
- Docker / Docker Compose
- GitHub Actions

---

## Переменные окружения

В проекте используется файл `.env`.

Пример содержимого `.env` для локального запуска и Docker:

```env
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=django-insecure-very-long-demo-secret-key-1234567890
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

POSTGRES_DB=habits
POSTGRES_USER=habits_user
POSTGRES_PASSWORD=habits_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

REDIS_HOST=localhost
REDIS_PORT=6379

CELERY_TIMEZONE=Europe/Moscow
```

Если в проекте настроена переменная `DATABASE_URL`, можно использовать явный вариант:

```env
DATABASE_URL=postgres://habits_user:habits_password@localhost:5432/habits
```

---

## Установка и запуск без Docker

1. Клонировать репозиторий.
2. Создать и активировать виртуальное окружение.
3. Установить зависимости.

Если используется Poetry:

```bash
poetry install
poetry shell
```

Или pip:

```bash
pip install -r requirements.txt
```

4. Создать `.env` (пример выше).
5. Применить миграции:

```bash
python manage.py migrate
```

6. Создать суперпользователя:

```bash
python manage.py createsuperuser
```

7. Запустить сервер:

```bash
python manage.py runserver
```

---

## Docker

В проекте присутствуют `Dockerfile` и `docker-compose.yml`.  
Судя по составу контейнеров, окружение включает:

- `web` — Django-приложение;
- `db` — PostgreSQL;
- `redis` — брокер/хранилище для фоновых задач;
- `celery` — воркер Celery;
- `nginx` — прокси.

### Запуск

Сборка и старт:

```bash
docker compose up --build
```

Запуск в фоне:

```bash
docker compose up -d --build
```

Остановка:

```bash
docker compose down
```

### Миграции внутри контейнера

Если сервис приложения называется `web`:

```bash
docker compose exec web python manage.py migrate
```

### Создание суперпользователя

```bash
docker compose exec web python manage.py createsuperuser
```

### Проверка контейнеров

```bash
docker ps
```

---

## CI (GitHub Actions)

В репозитории настроен workflow `.github/workflows/ci.yml`.

Что делает CI:

- Запускается на `push`.
- Поднимает сервисы:
  - `postgres:15`
  - `redis:7`
- Использует health-check для Postgres и Redis.
- Запускает тесты Django/DRF (команда зависит от вашего файла workflow).

### Secrets для CI

По текущей конфигурации workflow для Postgres используются секреты:

- `NAME`
- `USER`
- `PASSWORD`

Их нужно добавить в репозиторий:

`Settings → Secrets and variables → Actions → New repository secret`

Рекомендуемые значения:

- `NAME` = `habits`
- `USER` = `habits_user`
- `PASSWORD` = `habits_password`

Если вы захотите привести к более стандартному виду, можно переименовать секреты и переменные в workflow на:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

---

## Тесты

Локальный запуск:

```bash
python manage.py test
```

Или через pytest (если подключён):

```bash
pytest
```

В Docker:

```bash
docker compose exec web python manage.py test
```

---

## Структура приложения (кратко)

- `config/` — настройки проекта Django.
- `habits/` — приложение привычек:
  - `models.py` — модель Habit
  - `serializers.py`, `views.py`, `validators.py`, `tasks.py`
- `.github/workflows/ci.yml` — CI пайплайн.
- `docker-compose.yml`, `Dockerfile`, `nginx/` — контейнеризация и прокси.

---

## Лицензия

Учебный проект.

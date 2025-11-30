from datetime import timedelta

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate

from habits.models import Habit
from habits.permissions import IsOwnerOrReadOnly
from habits.serializers import HabitSerializer
from habits.tasks import send_habit_reminders
from habits.validators import validate_habit_business_rules
from habits.views import HabitViewSet

User = get_user_model()


class HabitModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", password="strongpass123")

    def test_str_representation_contains_user_type_and_action(self):
        habit = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=timezone.now().time(),
            action="Выпить воду",
            is_pleasant=False,
            periodicity=1,
            time_to_complete=60,
            is_public=False,
        )
        s = str(habit)
        self.assertIn("полезная привычка", s)
        self.assertIn("Выпить воду", s)
        self.assertIn(self.user.username, s)


class HabitBusinessRulesValidatorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="validator_user", password="strongpass123")
        self.pleasant_habit = Habit.objects.create(
            user=self.user,
            place="Кино",
            time=timezone.now().time(),
            action="Посмотреть фильм",
            is_pleasant=True,
            periodicity=1,
            time_to_complete=60,
            is_public=False,
        )
        self.useful_habit = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=timezone.now().time(),
            action="Сделать зарядку",
            is_pleasant=False,
            periodicity=1,
            time_to_complete=60,
            is_public=False,
        )

    def test_reward_and_related_habit_are_mutually_exclusive(self):
        attrs = {
            "is_pleasant": False,
            "reward": "Шоколад",
            "related_habit": self.pleasant_habit,
            "periodicity": 1,
            "time_to_complete": 60,
        }
        with self.assertRaisesMessage(Exception, "Нельзя одновременно указывать вознаграждение"):
            try:
                validate_habit_business_rules(attrs)
            except Exception as exc:
                # Убедимся, что это ValidationError с нужными полями
                self.assertIn("reward", getattr(exc, "detail", {}))
                self.assertIn("related_habit", getattr(exc, "detail", {}))
                raise

    def test_time_to_complete_cannot_exceed_120(self):
        attrs = {
            "is_pleasant": False,
            "periodicity": 1,
            "time_to_complete": 130,
        }
        with self.assertRaisesMessage(Exception, "Время на выполнение привычки не может превышать 120 секунд"):
            try:
                validate_habit_business_rules(attrs)
            except Exception as exc:
                self.assertIn("time_to_complete", getattr(exc, "detail", {}))
                raise

    def test_related_habit_must_be_pleasant(self):
        # useful_habit is not pleasant
        attrs = {
            "is_pleasant": False,
            "related_habit": self.useful_habit,
            "periodicity": 1,
            "time_to_complete": 60,
        }
        with self.assertRaisesMessage(Exception, "В связанные привычки могут попадать только приятные привычки"):
            try:
                validate_habit_business_rules(attrs)
            except Exception as exc:
                self.assertIn("related_habit", getattr(exc, "detail", {}))
                raise

    def test_pleasant_habit_cannot_have_reward_or_related_habit(self):
        attrs = {
            "is_pleasant": True,
            "reward": "Шоколад",
            "related_habit": self.pleasant_habit,
            "periodicity": 1,
            "time_to_complete": 60,
        }
        with self.assertRaises(Exception):
            try:
                validate_habit_business_rules(attrs)
            except Exception as exc:
                self.assertIn("reward", getattr(exc, "detail", {}))
                self.assertIn("related_habit", getattr(exc, "detail", {}))
                raise

    def test_periodicity_out_of_range_is_invalid(self):
        attrs = {
            "is_pleasant": False,
            "periodicity": 10,
            "time_to_complete": 60,
        }
        with self.assertRaises(Exception):
            try:
                validate_habit_business_rules(attrs)
            except Exception as exc:
                self.assertIn("periodicity", getattr(exc, "detail", {}))
                raise

    def test_periodicity_non_integer_is_invalid(self):
        attrs = {
            "is_pleasant": False,
            "periodicity": "abc",
            "time_to_complete": 60,
        }
        with self.assertRaises(Exception):
            try:
                validate_habit_business_rules(attrs)
            except Exception as exc:
                self.assertIn("periodicity", getattr(exc, "detail", {}))
                raise

    def test_partial_update_uses_instance_values(self):
        # instance already has reward, attrs only add related_habit → должна сработать проверка взаимного исключения
        instance = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=timezone.now().time(),
            action="Читать книгу",
            is_pleasant=False,
            reward="Чай",
            periodicity=1,
            time_to_complete=60,
            is_public=False,
        )
        attrs = {
            "related_habit": self.pleasant_habit,
        }
        with self.assertRaises(Exception):
            try:
                validate_habit_business_rules(attrs, instance=instance)
            except Exception as exc:
                self.assertIn("reward", getattr(exc, "detail", {}))
                self.assertIn("related_habit", getattr(exc, "detail", {}))
                raise


class HabitSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="serializer_user", password="strongpass123")
        self.factory = APIRequestFactory()

    def test_create_uses_request_user(self):
        request = self.factory.post("/habits/")
        request.user = self.user

        data = {
            "place": "Дом",
            "time": timezone.now().time().strftime("%H:%M:%S"),
            "action": "Выпить воду",
            "is_pleasant": False,
            "periodicity": 1,
            "time_to_complete": 60,
            "is_public": False,
        }

        serializer = HabitSerializer(data=data, context={"request": request})
        self.assertTrue(serializer.is_valid(), serializer.errors)

        habit = serializer.save()

        self.assertEqual(habit.user, self.user)

    def test_update_does_not_allow_user_change(self):
        habit = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=timezone.now().time(),
            action="Выпить воду",
            is_pleasant=False,
            periodicity=1,
            time_to_complete=60,
            is_public=False,
        )
        other_user = User.objects.create_user(username="other", password="strongpass123")

        data = {
            "user": other_user.id,
            "action": "Новое действие",
        }
        serializer = HabitSerializer(instance=habit, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        updated = serializer.save()

        self.assertEqual(updated.user, self.user)
        self.assertEqual(updated.action, "Новое действие")


class IsOwnerOrReadOnlyPermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="strongpass123")
        self.other_user = User.objects.create_user(username="other", password="strongpass123")
        self.habit = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=timezone.now().time(),
            action="Выпить воду",
            is_pleasant=False,
            periodicity=1,
            time_to_complete=60,
            is_public=False,
        )
        self.permission = IsOwnerOrReadOnly()

    def test_owner_has_object_permission(self):
        request = APIRequestFactory().get("/some-url/")
        request.user = self.user

        self.assertTrue(self.permission.has_object_permission(request, None, self.habit))

    def test_other_user_has_no_object_permission(self):
        request = APIRequestFactory().get("/some-url/")
        request.user = self.other_user

        self.assertFalse(self.permission.has_object_permission(request, None, self.habit))


class HabitViewSetAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", password="strongpass123")
        self.other_user = User.objects.create_user(username="user2", password="strongpass123")
        self.list_url = reverse("habits:habit-list")

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_auth_required_for_list(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_only_current_user_habits(self):
        Habit.objects.create(
            user=self.user,
            place="Дом",
            time=timezone.now().time(),
            action="Моя привычка",
            is_pleasant=False,
            periodicity=1,
            time_to_complete=60,
            is_public=False,
        )
        Habit.objects.create(
            user=self.other_user,
            place="Офис",
            time=timezone.now().time(),
            action="Чужая привычка",
            is_pleasant=False,
            periodicity=1,
            time_to_complete=60,
            is_public=False,
        )

        self.authenticate(self.user)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["action"], "Моя привычка")

    def test_create_habit_sets_user_to_request_user(self):
        self.authenticate(self.user)
        payload = {
            "place": "Дом",
            "time": timezone.now().time().strftime("%H:%M:%S"),
            "action": "Выпить воду",
            "is_pleasant": False,
            "periodicity": 1,
            "time_to_complete": 60,
            "is_public": False,
        }

        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        habit = Habit.objects.get(id=response.data["id"])
        self.assertEqual(habit.user, self.user)

    def test_cannot_access_other_users_habit(self):
        habit_other = Habit.objects.create(
            user=self.other_user,
            place="Офис",
            time=timezone.now().time(),
            action="Чужая привычка",
            is_pleasant=False,
            periodicity=1,
            time_to_complete=60,
            is_public=False,
        )
        detail_url = reverse("habits:habit-detail", args=[habit_other.id])

        self.authenticate(self.user)
        response = self.client.get(detail_url)

        # Из-за фильтра в get_queryset чужие привычки просто не видны → 404
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_pagination_page_size_two(self):
        self.authenticate(self.user)
        for i in range(3):
            Habit.objects.create(
                user=self.user,
                place=f"Место {i}",
                time=timezone.now().time(),
                action=f"Привычка {i}",
                is_pleasant=False,
                periodicity=1,
                time_to_complete=60,
                is_public=False,
            )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIsNotNone(response.data["next"])


class PublicHabitListViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="public_user", password="strongpass123")
        self.url = reverse("habits:public-habits")

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def test_auth_required_for_public_habits(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_only_public_habits(self):
        Habit.objects.create(
            user=self.user,
            place="Дом",
            time=timezone.now().time(),
            action="Публичная 1",
            is_pleasant=False,
            periodicity=1,
            time_to_complete=60,
            is_public=True,
        )
        Habit.objects.create(
            user=self.user,
            place="Дом",
            time=timezone.now().time(),
            action="Публичная 2",
            is_pleasant=False,
            periodicity=1,
            time_to_complete=60,
            is_public=True,
        )
        Habit.objects.create(
            user=self.user,
            place="Дом",
            time=timezone.now().time(),
            action="Приватная",
            is_pleasant=False,
            periodicity=1,
            time_to_complete=60,
            is_public=False,
        )

        self.authenticate()
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        actions = {item["action"] for item in response.data["results"]}
        self.assertEqual(actions, {"Публичная 1", "Публичная 2"})


class HabitViewSetDirectCallTests(TestCase):
    """
    Небольшой прямой тест ViewSet через APIRequestFactory,
    чтобы убедиться, что get_queryset фильтрует по пользователю.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="factory_user", password="strongpass123")
        self.other_user = User.objects.create_user(username="factory_other", password="strongpass123")
        Habit.objects.create(
            user=self.user,
            place="Дом",
            time=timezone.now().time(),
            action="Моя привычка",
            is_pleasant=False,
            periodicity=1,
            time_to_complete=60,
            is_public=False,
        )
        Habit.objects.create(
            user=self.other_user,
            place="Офис",
            time=timezone.now().time(),
            action="Чужая привычка",
            is_pleasant=False,
            periodicity=1,
            time_to_complete=60,
            is_public=False,
        )
        self.factory = APIRequestFactory()

    def test_get_queryset_returns_only_user_habits(self):
        view = HabitViewSet.as_view({"get": "list"})
        request = self.factory.get("/habits/")
        force_authenticate(request, user=self.user)
        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["action"], "Моя привычка")


class SendHabitRemindersTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="task_user",
            password="strongpass123",
            telegram_chat_id=123456,
        )

    @override_settings(TELEGRAM_API_URL="https://test-api", TELEGRAM_BOT_TOKEN="TEST_TOKEN")
    @patch("habits.tasks.requests.post")
    @patch("django.utils.timezone.localtime")
    def test_send_habit_reminders_sends_message_for_matching_habit(
        self,
        mock_localtime,
        mock_post,
    ):
        now = timezone.now().replace(second=0, microsecond=0)
        if timezone.is_naive(now):
            now = timezone.make_aware(now, timezone.get_current_timezone())
        mock_localtime.return_value = now

        habit = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=now.time(),
            action="Выпить воду",
            is_pleasant=False,
            periodicity=1,
            time_to_complete=60,
            is_public=False,
        )

        send_habit_reminders()

        self.assertTrue(mock_post.called)
        args, kwargs = mock_post.call_args
        url = args[0]
        self.assertIn("https://test-api", url)
        self.assertIn("botTEST_TOKEN/sendMessage", url)
        self.assertEqual(kwargs["json"]["chat_id"], self.user.telegram_chat_id)
        self.assertIn("Выпить воду", kwargs["json"]["text"])
        self.assertIn(habit.place, kwargs["json"]["text"])

    @override_settings(TELEGRAM_API_URL="https://test-api", TELEGRAM_BOT_TOKEN="TEST_TOKEN")
    @patch("habits.tasks.requests.post")
    @patch("django.utils.timezone.localtime")
    def test_send_habit_reminders_respects_periodicity(
        self,
        mock_localtime,
        mock_post,
    ):
        now = timezone.now().replace(second=0, microsecond=0)
        if timezone.is_naive(now):
            now = timezone.make_aware(now, timezone.get_current_timezone())
        mock_localtime.return_value = now

        habit = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=now.time(),
            action="Привычка с периодичностью 2 дня",
            is_pleasant=False,
            periodicity=2,
            time_to_complete=60,
            is_public=False,
        )
        # сделаем так, чтобы с даты создания прошёл 1 день → напоминания быть не должно
        habit.created_at = now - timedelta(days=1)
        habit.save(update_fields=["created_at"])

        send_habit_reminders()

        mock_post.assert_not_called()


from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.serializers import UserRegisterSerializer

User = get_user_model()


class UserModelTests(TestCase):
    def test_str_returns_username(self):
        user = User.objects.create_user(username="testuser", password="strongpass123")
        self.assertEqual(str(user), "testuser")


class UserRegisterSerializerTests(TestCase):
    def test_create_user_with_hashed_password(self):
        data = {
            "username": "serializer_user",
            "email": "user@example.com",
            "password": "strongpass123",
        }
        serializer = UserRegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save()

        self.assertIsInstance(user, User)
        self.assertNotEqual(user.password, data["password"])
        self.assertTrue(user.check_password(data["password"]))

    def test_short_password_is_invalid(self):
        data = {
            "username": "shortpass",
            "email": "user@example.com",
            "password": "1234567",  # меньше 8 символов
        }
        serializer = UserRegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)


class RegisterViewTests(APITestCase):
    def test_register_creates_user_and_returns_201(self):
        url = reverse("users:register")
        payload = {
            "username": "apiuser",
            "email": "api@example.com",
            "password": "strongpass123",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get(username="apiuser")
        self.assertTrue(user.check_password("strongpass123"))

    def test_register_returns_validation_error_for_invalid_data(self):
        url = reverse("users:register")
        payload = {
            "username": "",
            "password": "123",  # и короткий, и username пустой
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        self.assertIn("password", response.data)


class TelegramWebhookTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="telegram_user",
            password="strongpass123",
        )
        self.url = reverse("users:telegram-webhook")

    def test_webhook_without_chat_id_returns_200_and_does_not_change_user(self):
        payload = {
            "message": {
                "chat": {},
                "text": "hello",
            }
        }

        old_chat_id = self.user.telegram_chat_id

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.telegram_chat_id, old_chat_id)

    def test_webhook_with_unknown_username_returns_200_without_side_effects(self):
        payload = {
            "message": {
                "chat": {
                    "id": 123456,
                    "username": "unknown_user",
                },
                "text": "hello",
            }
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.telegram_chat_id)

    def test_webhook_updates_telegram_chat_id_for_existing_user(self):
        payload = {
            "message": {
                "chat": {
                    "id": 555555,
                    "username": self.user.username,
                },
                "text": "hello",
            }
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.telegram_chat_id, 555555)

    @override_settings(
        TELEGRAM_API_URL="https://test-api", TELEGRAM_BOT_TOKEN="TEST_TOKEN"
    )
    @patch("requests.post")
    def test_webhook_start_command_sends_greeting_message(self, mock_post):
        chat_id = 777777
        payload = {
            "message": {
                "chat": {
                    "id": chat_id,
                    "username": self.user.username,
                },
                "text": "/start",
            }
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.telegram_chat_id, chat_id)

        self.assertTrue(mock_post.called)
        args, kwargs = mock_post.call_args
        url = args[0]
        self.assertIn("https://test-api", url)
        self.assertIn("botTEST_TOKEN/sendMessage", url)
        self.assertEqual(kwargs["json"]["chat_id"], chat_id)
        self.assertIn("Привет!", kwargs["json"]["text"])


class JWTAuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="jwtuser",
            password="strongpass123",
        )

    def test_obtain_token_pair(self):
        url = reverse("users:token_obtain_pair")
        payload = {
            "username": "jwtuser",
            "password": "strongpass123",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_refresh_token(self):
        obtain_url = reverse("users:token_obtain_pair")
        refresh_url = reverse("users:token_refresh")

        obtain_resp = self.client.post(
            obtain_url,
            {"username": "jwtuser", "password": "strongpass123"},
            format="json",
        )
        refresh_token = obtain_resp.data["refresh"]

        response = self.client.post(
            refresh_url, {"refresh": refresh_token}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

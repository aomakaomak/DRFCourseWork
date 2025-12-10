from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UserRegisterSerializer

User = get_user_model()


class RegisterView(APIView):
    """
    Эндпоинт регистрации нового пользователя.
    Доступен без авторизации.
    """

    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def telegram_webhook(request):
    """
    Webhook для Telegram бота.

    Ожидаем входящие обновления от Telegram.
    Если приходит сообщение от пользователя, пробуем найти его по username
    и сохранить chat_id в его профиле.
    """
    data = request.data

    message = data.get("message") or {}
    chat = message.get("chat") or {}
    text = message.get("text") or ""
    chat_id = chat.get("id")
    username = chat.get("username")

    if not chat_id:
        return Response(status=200)

    if username:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(status=200)

        if user.telegram_chat_id != chat_id:
            user.telegram_chat_id = chat_id
            user.save(update_fields=["telegram_chat_id"])

    if text.strip() == "/start":
        from django.conf import settings
        import requests

        url = (
            f"{settings.TELEGRAM_API_URL}/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        )
        requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": "Привет! Я буду напоминать тебе о твоих привычках.",
            },
        )

    return Response(status=200)

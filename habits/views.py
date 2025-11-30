from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Habit
from .pagination import HabitPagination
from .permissions import IsOwnerOrReadOnly
from .serializers import HabitSerializer


class HabitViewSet(viewsets.ModelViewSet):
    """
    CRUD для привычек текущего пользователя.

    - list:   список привычек текущего пользователя с пагинацией
    - create: создание привычки (user = request.user)
    - retrieve/update/partial_update/destroy: только свои привычки
    """

    serializer_class = HabitSerializer
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    pagination_class = HabitPagination

    def get_queryset(self):
        """
        Возвращаем только привычки текущего пользователя.
        Это автоматически ограничивает и list, и retrieve, и update, и destroy.
        """
        return Habit.objects.filter(user=self.request.user).order_by("time", "place")

    def perform_create(self, serializer):
        """
        Привязываем привычку к текущему пользователю.
        """
        serializer.save(user=self.request.user)


class PublicHabitListView(generics.ListAPIView):
    """
    Список публичных привычек (is_public=True).

    По ТЗ: "Пользователь может видеть список публичных привычек без
    возможности их редактировать или удалять."

    Здесь только GET, без изменений.
    """

    serializer_class = HabitSerializer
    permission_classes = (
        IsAuthenticated,
    )  # можно заменить на AllowAny при необходимости
    pagination_class = HabitPagination

    def get_queryset(self):
        return Habit.objects.filter(is_public=True).order_by("time", "place")

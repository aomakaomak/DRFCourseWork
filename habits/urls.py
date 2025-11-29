from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .apps import HabitsConfig
from .views import HabitViewSet, PublicHabitListView

app_name = HabitsConfig.name

router = DefaultRouter()
router.register(r"habits", HabitViewSet, basename="habit")

urlpatterns = [
    # CRUD для привычек текущего пользователя
    path("", include(router.urls)),

    # Список публичных привычек
    path(
        "public-habits/",
        PublicHabitListView.as_view(),
        name="public-habits",
    ),
]

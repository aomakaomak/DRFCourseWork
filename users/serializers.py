from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")
        read_only_fields = ("id",)
        extra_kwargs = {
            "email": {"required": False, "allow_blank": True},
        }

    def create(self, validated_data):
        """
        Создаём пользователя через create_user, чтобы пароль хэшировался.
        Для кастомной модели на базе AbstractUser это корректный путь.
        """
        username = validated_data.get("username")
        email = validated_data.get("email", "")
        password = validated_data.get("password")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        return user

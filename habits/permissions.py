from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """
    Доступ к объекту только владельцу.
    Чтение/запросы к чужим привычкам через этот permission запрещены.
    """

    def has_object_permission(self, request, view, obj):
        # Только владелец может читать/изменять/удалять
        return obj.user == request.user

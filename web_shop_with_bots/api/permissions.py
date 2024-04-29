from rest_framework.permissions import BasePermission


class IsOwnerOrAdmin(BasePermission):
    """
    Запросы доступны только для админа и зарегестрированного пользователя.
    (для получения информации о клиенте и заполнения формы заказа).
    """
    def has_object_permission(self, request, view, obj):
        if obj == request.user.base_profile:
            return True
        return request.user.is_admin()


class MyIsAdmin(BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user.is_admin())


class DenyAllPermission(BasePermission):
    """
    Deny permission to all users.
    """

    def has_permission(self, request, view):
        return False

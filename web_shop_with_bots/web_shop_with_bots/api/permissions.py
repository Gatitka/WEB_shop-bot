from rest_framework.permissions import BasePermission


class DenyAllPermission(BasePermission):
    def has_permission(self, request, view):
        # Всегда запрещаем доступ
        return False

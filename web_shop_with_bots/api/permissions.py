# from rest_framework.permissions import IsAuthenticatedOrReadOnly


# class IsAuthorAdminOrReadOnly(IsAuthenticatedOrReadOnly):
#     """
#     Без авторизации доступны только запросы на чтение, для создания новой
#     записи пользователь должен быть авторизован.
#     Редактировать или удалять записи может только их автор или
#     админ с модератором.
#     """
#     def has_object_permission(self, request, view, obj):
#         if view.action == 'retrieve' or obj.author == request.user:
#             return True
#         return request.user.is_admin()

from django.contrib.auth import get_user_model
from catalog.models import Dish
from shop.models import ShoppingCart, CartDish, Shop, Delivery
from django.shortcuts import get_object_or_404, redirect
from api.utils import check_existance_create_delete
from rest_framework.decorators import action
from .serializers import WebAccauntSerializer, SignUpSerializer, PasswordSerializer, DishShortSerializer,ShopSerializer, DeliverySerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import mixins, status, viewsets
from rest_framework.views import APIView
from rest_framework.decorators import api_view

# import base64
# from django.utils.encoding import force_text
# from django.contrib.auth.tokens.PasswordResetTokenGenerator import default_token_generator


User = get_user_model()


DATE_TIME_FORMAT = '%d/%m/%Y %H:%M'


def activateuseraccount(request, uidb64=None, token=None):
# print(force_text(urlsafe_base64_decode(uidb64)))
    # print(token)
    try:
        uid = force_text(base64.urlsafe_base64_decode(uidb64))
        #print(type(uid),uid)
        user = User.objects.get(pk=uid)
        print(user)
    except User.DoesNotExist:
        user = None
    if user and default_token_generator.check_token(user, token):
        user.is_email_verified = True
        user.is_active = True
        user.save()
        login(request,user)
        print("Activaton done")
    else:
        print("Activation failed")


class ShopViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Работает с ресторанами.
    Изменение и создание тэгов разрешено только через админку.
    """
    serializer_class = ShopSerializer
    pagination_class = None



@api_view(['GET'])
def contacts_delivery(request):
    shops = Shop.objects.filter(is_active=True).all()
    delivery = Delivery.objects.filter(is_active=True).filter(type=1).all()
    response_data = {}
    response_data['shops'] = ShopSerializer(shops, many=True).data
    response_data['delivery'] = DeliverySerializer(delivery).data
    return Response(response_data)





class UserActivationView(APIView):
    def get(self, request, uid, token):
        protocol = 'https://' if request.is_secure() else 'http://'
        web_url = protocol + request.get_host()
        post_url = web_url + "/auth/users/activation/"
        post_data = {'uid': uid, 'token': token}
        result = request.post(post_url, data = post_data)
        content = result.text()
        return Response(content)


class MyUserViewSet(mixins.CreateModelMixin,
                    mixins.RetrieveModelMixin,
                    viewsets.GenericViewSet):
    """
    Вьюсет модели WebAcount и BaseProfile для создания
    нового пользователя, изменения пароля,
    просмотра актуального пользователя (/me).


    """
    queryset = User.objects.all()
    serializer_class = WebAccauntSerializer
    permission_classes = [AllowAny]

    def get_instance(self):
        return self.request.user

    def get_serializer_class(self):
        if self.action in ["create", "partial_update"]:
            return SignUpSerializer
        return self.serializer_class

    @action(
        detail=False,
        methods=['get'],
        serializer_class=WebAccauntSerializer,
        permission_classes=[IsAuthenticated],
        url_path='me'
    )
    def user_profile(self, request):
        """
        Экшен для обработки страницы актуального пользователя
        api/users/me. Только GET, PATCH запросы
        """
        self.get_object = self.get_instance
        if request.method == "GET":
            return self.retrieve(request)
        return self.partial_update(request)

    @action(detail=False,
            methods=['post'],
            permission_classes=[IsAuthenticated])
    def set_password(self, request):
        """
        Экшен для обработки страницы смены пароля
        api/users/set_password.
        Только POST запросы.
        """
        user = request.user
        request.data['user'] = user
        serializer = PasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(request.data['new_password'])
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def orders(self, request):
        """
        Экшен для обработки страницы заказов
        api/users/orders.
        Только GET запросы.
        """
        self.get_object = self.get_instance
        if request.method == "GET":
            return self.retrieve(request)
        return self.partial_update(request)


class MenuViewSet(mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    """
    Вьюсет для работы с меню и моделью Dish.
    Просмотр меню и отдельных блюд.

    Для авторизованных и неавторизованных пользователей —
    возможность добавить/удалить блюдо из корзины.

    Queryset фильтруется кастомным фильтром RecipeFilter по параметрам запроса
    и выдает список всех рецептов/нахоядщихся в корзине.
    """
    # permission_classes = [IsAuthorAdminOrReadOnly]
    serializer_class = DishShortSerializer
    # filter_backends = (DjangoFilterBackend,)
    # filterset_class = RecipeFilter
    queryset = Dish.objects.select_related(
        'category'
    ).all

    # @action(detail=True,
    #         methods=['post', 'delete'])
    # def shopping_cart(self, request, pk=None):
    #     """
    #     Добавляет/удалет блюдо в `список покупок`.

    #     Args:
    #         request (WSGIRequest): Объект запроса.
    #         pk (int):
    #             id блюда, которое нужно добавить/удалить в `корзину покупок`.

    #     Returns:
    #         Responce: Статус подтверждающий/отклоняющий действие.
    #     """
    #     current_user = request.user
    #     dish = get_object_or_404(Dish, id=pk)
    #     method = request.method
    #     return_obj = 'response'
    #     cart = ShoppingCart.objects.get_or_create(user=current_user)



    #     return check_existance_create_delete(CartDish, method,
    #                                          return_obj,
    #                                          RecipesShortSerializer, dish,
    #                                          cart=cart,
    #                                          dish=dish)



















# from django.contrib.auth import get_user_model
# from django.db.models import Count, F, Sum
# from django.http import HttpResponse
# from django.shortcuts import get_object_or_404, redirect
# from django.utils import timezone
# from django_filters.rest_framework import DjangoFilterBackend
# from rest_framework import mixins, status, viewsets
# from rest_framework.decorators import action
# from rest_framework.permissions import AllowAny, IsAuthenticated
# from rest_framework.response import Response

# from api.filters import IngredientFilter, RecipeFilter
# from api.permissions import IsAuthorAdminOrReadOnly
# from api.serializers import (IngredientSerializer, PasswordSerializer,
#                              RecipeSerializer, RecipesShortSerializer,
#                              SignUpSerializer, SubscriptionsSerializer,
#                              TagSerializer, UserSerializer)
# from api.utils import check_existance_create_delete
# from recipe.models import Favorit, Ingredient, Recipe, ShoppingCartUser, Tag
# from user.models import Subscription

# User = get_user_model()


# DATE_TIME_FORMAT = '%d/%m/%Y %H:%M'


# class MyUserViewSet(mixins.CreateModelMixin,
#                     mixins.RetrieveModelMixin,
#                     mixins.ListModelMixin,
#                     viewsets.GenericViewSet):
#     """
#     Вьюсет модели User для отображения списка пользователей, создания
#     нового пользователя, изменения пароля, просмотра конкретного
#     пользователя, актуального пользователя (/me),
#     страницы подписок (/subscriptions).

#     """
#     queryset = User.objects.all()
#     serializer_class = UserSerializer
#     permission_classes = [AllowAny]

#     def get_instance(self):
#         return self.request.user

#     def get_serializer_class(self):
#         if self.action in ["create", "partial_update"]:
#             return SignUpSerializer
#         return self.serializer_class

#     @action(
#         detail=False,
#         methods=['get'],
#         serializer_class=UserSerializer,
#         permission_classes=[IsAuthenticated],
#         url_path='me'
#     )
#     def user_profile(self, request):
#         """
#         Экшен для обработки страницы актуального пользователя
#         api/users/me. Только GET, PATCH запросы
#         """
#         self.get_object = self.get_instance
#         if request.method == "GET":
#             return self.retrieve(request)
#         return self.partial_update(request)

#     @action(detail=False,
#             methods=['post'],
#             permission_classes=[IsAuthenticated])
#     def set_password(self, request):
#         """
#         Экшен для обработки страницы смены пароля
#         api/users/set_password.
#         Только POST запросы.
#         """
#         user = request.user
#         request.data['user'] = user
#         serializer = PasswordSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user.set_password(request.data['new_password'])
#         user.save()
#         return Response(status=status.HTTP_204_NO_CONTENT)

#     @action(detail=False,
#             methods=['get'],
#             permission_classes=[IsAuthenticated]
#             )
#     def subscriptions(self, request):
#         """
#         Экшен для получения данных об авторах, находящихся в подписках у
#         актуального пользователя, а так же их подписках.
#         Только GET запросы.
#         """
#         queryset = User.objects.filter(
#             following__user=self.request.user
#         ).annotate(recipes_count=Count('recipes'))
#         page = self.paginate_queryset(queryset)
#         if page is not None:
#             serializer = SubscriptionsSerializer(page, many=True)
#             serializer.context['request'] = request
#             serializer.context[
#                 'recipes_limit'
#             ] = request.query_params.get('recipes_limit')
#             return self.get_paginated_response(serializer.data)

#         serializer = SubscriptionsSerializer(queryset, many=True)
#         serializer.context['request'] = request
#         serializer.context[
#             'recipes_limit'
#         ] = request.query_params.get('recipes_limit')
#         return Response(serializer.data)

#     @action(detail=True,
#             methods=['get', 'post', 'delete'],
#             permission_classes=[IsAuthenticated]
#             )
#     def subscribe(self, request, pk=None):
#         """
#         Экшен для получения данных об авторах, находящихся в подписках у
#         актуального пользователя, а так же их подписках.
#         Только GET запросы.
#         """
#         current_user = request.user
#         author = get_object_or_404(User, id=pk)
#         if self.request.user == author:
#             return Response(f'{"Проверьте выбранного автора. "}'
#                             f'{"Подписка на свой аккаунт невозможна."}',
#                             status=status.HTTP_400_BAD_REQUEST)

#         method = request.method
#         return_obj = 'redirect'
#         return_v = check_existance_create_delete(Subscription, method,
#                                                  return_obj,
#                                                  SubscriptionsSerializer,
#                                                  author,
#                                                  user=current_user,
#                                                  author=author)
#         if return_v != 'redirect':
#             return return_v
#         return redirect(
#             'api:user-detail',
#             pk=author.id
#         )


# class RecipeViewSet(mixins.CreateModelMixin,
#                     mixins.DestroyModelMixin,
#                     mixins.RetrieveModelMixin,
#                     mixins.ListModelMixin,
#                     mixins.UpdateModelMixin,
#                     viewsets.GenericViewSet):
#     """
#     Вьюсет для работы с моделью Recipe.
#     Просмотр, создание, редактирование рецепта.
#     Изменять рецепт может только автор или админы.

#     Для авторизованных пользователей — возможность добавить/удалить
#     рецепт в избранное и в список покупок
#     + скачать список покупок текстовым файлом.

#     Queryset фильтруется кастомным фильтром RecipeFilter по параметрам запроса
#     и выдает список всех рецептов/избранных/нахоядщихся в корзине.
#     """
#     permission_classes = [IsAuthorAdminOrReadOnly]
#     serializer_class = RecipeSerializer
#     filter_backends = (DjangoFilterBackend,)
#     filterset_class = RecipeFilter
#     queryset = Recipe.objects.select_related(
#         'author'
#     ).all(
#     ).prefetch_related(
#         'tags', 'ingredients'
#     )

#     @action(detail=True,
#             methods=['post', 'delete'])
#     def favorite(self, request, pk=None):
#         """Добавляет/удалет рецепт в `избранное`.

#         Args:
#             request (WSGIRequest): Объект запроса.
#             pk (int):
#                 id рецепта, который нужно добавить/удалить из `избранного`.

#         Returns:
#             Responce: Статус подтверждающий/отклоняющий действие.
#         """
#         current_user = request.user
#         recipe = get_object_or_404(Recipe, id=pk)
#         method = request.method
#         return_obj = 'response'

#         return check_existance_create_delete(Favorit, method, return_obj,
#                                              RecipesShortSerializer, recipe,
#                                              favoriter=current_user,
#                                              recipe=recipe)

#     @action(detail=True,
#             methods=['post', 'delete'])
#     def shopping_cart(self, request, pk=None):
#         """
#         Добавляет/удалет рецепт в `список покупок`.

#         Args:
#             request (WSGIRequest): Объект запроса.
#             pk (int):
#                 id рецепта, который нужно добавить/удалить в `корзину покупок`.

#         Returns:
#             Responce: Статус подтверждающий/отклоняющий действие.
#         """
#         current_user = request.user
#         recipe = get_object_or_404(Recipe, id=pk)
#         method = request.method
#         return_obj = 'response'

#         return check_existance_create_delete(ShoppingCartUser, method,
#                                              return_obj,
#                                              RecipesShortSerializer, recipe,
#                                              owner=current_user,
#                                              recipe=recipe)

#     @action(detail=False,
#             methods=['get'],
#             permission_classes=[IsAuthenticated])
#     def download_shopping_cart(self, request):
#         """Скачивает файл *.txt со списком покупок.

#         Возвращает текстовый файл со списком ингредиентов из рецептов,
#         добавленных в корзину для покупки.
#         Колличесвто повторяющихся ингридиентов суммированно.
#         Вызов метода через url:  */recipes/download_shopping_cart/.

#         Args:
#             request (WSGIRequest): Объект запроса.

#         Returns:
#             Responce: Ответ с текстовым файлом.
#         """
#         user = self.request.user
#         if not ShoppingCartUser.objects.filter(
#                 owner=user
#         ).exists():
#             return Response(
#                 'Корзина покупок пользователя пуста.',
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         filename = f'{user.username}_shopping_list.txt'
#         shopping_list = [
#             f'Список покупок для:\n\n{user.first_name}\n'
#             f'Дата: {timezone.now().strftime(DATE_TIME_FORMAT)}\n'
#         ]

#         ingredients = Ingredient.objects.filter(
#             recipe__recipe__in_shopping_cart__owner=user
#         ).values(
#             'name',
#             measurement=F('measurement_unit')
#         ).annotate(amount=Sum('recipe__amount'))

#         for ing in ingredients:
#             shopping_list.append(
#                 f'{ing["name"]}: {ing["amount"]} {ing["measurement"]}'
#             )

#         shopping_list.append('\nХороших покупок! Твой Foodgram')
#         shopping_list = '\n'.join(shopping_list)
#         response = HttpResponse(
#             shopping_list, content_type='text.txt; charset=utf-8'
#         )
#         response['Content-Disposition'] = f'attachment; filename={filename}'
#         return response

#     def update(self, request, *args, **kwargs):
#         """
#         Ограничение для метода PUT. Редакция существующих рецептов только
#         через PATCH метод.
#         """

#         if request.method == "PUT":
#             return self.http_method_not_allowed(request, *args, **kwargs)
#         return super().update(request, *args, **kwargs)


# class TagViewSet(viewsets.ReadOnlyModelViewSet):
#     """
#     Работает с тэгами.
#     Изменение и создание тэгов разрешено только админам.
#     """
#     queryset = Tag.objects.all()
#     serializer_class = TagSerializer
#     pagination_class = None


# class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
#     """
#     Работет с ингредиентами.
#     Изменение и создание ингредиентов разрешено только админам.
#     """
#     queryset = Ingredient.objects.all()
#     serializer_class = IngredientSerializer
#     pagination_class = None
#     filter_backends = [IngredientFilter]
#     search_fields = ('^name',)

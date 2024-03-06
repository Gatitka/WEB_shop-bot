from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import UserSerializer
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import DestroyAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils.translation import get_language_from_request
from django.db.models import Prefetch
from catalog.models import Dish
from delivery_contacts.models import Delivery, Restaurant, DeliveryZone
from promos.models import PromoNews, Promocode
from shop.models import CartDish, Order, OrderDish, ShoppingCart
from users.models import BaseProfile, UserAddress
from django.urls import reverse
from django.http import JsonResponse
from django.utils.translation import activate
import logging
from .filters import CategoryFilter
from django.core.exceptions import ValidationError
from.serializers import (CartDishSerializer, DeliverySerializer,
                         DishMenuSerializer, PromoNewsSerializer,

                         ShoppingCartSerializer,
                         RestaurantSerializer,
                         RestaurantSerializer,
                         UserAddressSerializer,
                         UserOrdersSerializer,
                         ContatsDeliverySerializer,
                         TakeawayOrderSerializer,
                         TakeawayConditionsSerializer,
                         TakeawayOrderWriteSerializer,
                         DeliveryOrderSerializer,
                         DeliveryConditionsSerializer,
                         DeliveryOrderWriteSerializer,
                         )
                         # PreOrderDataSerializer,)
from decimal import Decimal
from shop.utils import get_cart, get_reply_data
from delivery_contacts.utils import get_delivery_cost_zone
from rest_framework.exceptions import ValidationError as DRFValidationError


logger = logging.getLogger(__name__)

User = get_user_model()


DATE_TIME_FORMAT = '%d/%m/%Y %H:%M'


class DeleteUserViewSet(DestroyAPIView):
    serializer_class = [UserSerializer]
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        instance = self.request.user
        instance.is_deleted = True
        logger.debug('web_account проставлена отметка is_deleted = True')
        instance.save()
        logger.debug('web_account сохранен')
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContactsDeliveryViewSet(mixins.ListModelMixin,
                              viewsets.GenericViewSet):
    """
    Вьюсет для адреса /contacts.
    Отображает список всех активных ресторанов
    и условия самовывоза во всех городах.
    Доступно только чтение спика
    """
    permission_classes = [AllowAny,]
    serializer_class = ContatsDeliverySerializer

    def list(self, request, *args, **kwargs):
        restaurants = Restaurant.objects.filter(is_active=True).all()
        logger.debug('получен список ресторанов')
        delivery = Delivery.objects.filter(
            is_active=True,
            ).all().prefetch_related('translations')
        logger.debug('получен список доставок')
        response_data = {}
        response_data['restaurants'] = RestaurantSerializer(
            restaurants,
            many=True).data
        response_data['delivery'] = DeliverySerializer(
            delivery,
            many=True).data
        logger.debug('списки ресторанов и доставки успешно сериализированны')
        return Response(response_data)


class MyAddressViewSet(mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.CreateModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.DestroyModelMixin,
                       viewsets.GenericViewSet):
    """
    Вьюсет модели UserAddresses для просмотра сохраненных адресов пользователя.
    """
    serializer_class = UserAddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserAddress.objects.filter(
            base_profile=self.request.user.base_profile
        ).all()

    def perform_create(self, serializer):
        serializer.save(base_profile=self.request.user.base_profile)

    def perform_update(self, serializer):
        serializer.save(base_profile=self.request.user.base_profile)


class ClientAddressesViewSet(mixins.ListModelMixin,
                             viewsets.GenericViewSet):
    """
    Вьюсет для всех пользователей для получения сохраненных адресов клиента.
    """
    serializer_class = UserAddressSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        if user_id is None or not user_id.isdigit():
            return Response("User ID is required")

        queryset = UserAddress.objects.filter(
            base_profile=int(user_id)
        ).values('address')
        return queryset


class PromoNewsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет модели PromoNews доступен только для чтения.
    Отбираются только новости is_active=True.
    """
    queryset = PromoNews.objects.filter(is_active=True).all().prefetch_related('translations')
    serializer_class = PromoNewsSerializer
    permission_classes = [AllowAny,]


class UserOrdersViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет модели Orders для просмотра истории заказов.
    """
    serializer_class = UserOrdersSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        my_orders = Order.objects.filter(
                user=self.request.user.base_profile
            ).all().prefetch_related(
                Prefetch(
                    'order_dishes',
                    queryset=OrderDish.objects.all().select_related(
                        'dish'
                    ).only(
                        'dish__image'
                    ).prefetch_related(
                        'dish__translations'
                    )
                )
            )[:3]
        if my_orders:
            return my_orders


class MenuViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    """
    Вьюсет для работы с меню и моделями Dish, Category.
    Просмотр меню и отдельных блюд.

    Для авторизованных и неавторизованных пользователей —
    возможность добавить/удалить блюдо из корзины.

    Queryset фильтруется кастомным фильтром RecipeFilter по параметрам запроса
    и выдает список всех рецептов/нахоядщихся в корзине.
    """
    permission_classes = [AllowAny,]
    serializer_class = DishMenuSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = CategoryFilter
    queryset = Dish.objects.filter(
        is_active=True,
        category__is_active=True
    ).all().select_related(
        'units_in_set_uom',
        'weight_volume_uom',
        ).prefetch_related(
        'translations',
        'category__translations',
        'units_in_set_uom__translations',
        'weight_volume_uom__translations',
    ).distinct().order_by('category__priority', 'priority')

    http_method_names = ['get', 'post']

    def list(self, request, *args, **kwargs):
        user = request.user

        response_data = {
                'dishes': None,
                'cart': None,
            }
        context = {'request': request}

        if user.is_authenticated:
            base_profile = BaseProfile.objects.select_related('shopping_cart').get(web_account=request.user)


            context['extra_kwargs'] = {'cart_items':
                                       base_profile.shopping_cart.dishes.all()}

            dish_serializer = self.get_serializer(self.get_queryset(),
                                                  many=True,
                                                  context=context,
                                                  )

            items_qty = base_profile.shopping_cart.items_qty
            response_data['cart'] = {'items_qty': items_qty}
        else:
            dish_serializer = self.get_serializer(self.get_queryset(),
                                                  many=True,
                                                  context=context)

        response_data['dishes'] = dish_serializer.data

        response_data = dish_serializer.data
        return Response(response_data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True,
            methods=['post'])   # , 'delete'])
    def add_to_shopping_cart(self, request, pk=None):
        """
        Добавление блюда в корзину из общего меню.\n
        Payload должен быть пустым, т.е. "weight_volume_uom",
        "units_in_set_uom" не нужны\n
        ID блюда передается в строке запроса.

        Args:
            request (WSGIRequest): Объект запроса.
            id (int):
                id блюда, которое нужно добавить в `корзину покупок`.

        Returns:
            Responce: Статус подтверждающий/отклоняющий действие.
        """
        method = request.META['REQUEST_METHOD']
        current_user = request.user

        if current_user.is_authenticated:
            dish = get_object_or_404(Dish, article=pk)
            cart, state = ShoppingCart.objects.get_or_create(user=current_user.base_profile)

            # try:
            #     cart = ShoppingCart.objects.get(session_id=request.session['hi'], completed=False)
            # except:
            #     request.session['hi'] = str(uuid.uuid4())
            #     cart = ShoppingCart.objects.get_or_create(session_id=request.session['hi'], completed=False)

            if method == 'POST':
                cartdish, created = CartDish.objects.get_or_create(
                    cart=cart, dish=dish)
                if not created:
                    cartdish.quantity += 1
                    cartdish.save(update_fields=['quantity', 'amount'])

                return Response({'cartdish': f'{cartdish.id}',
                                 'quantity': f'{cartdish.quantity}',
                                 'amount': f'{cartdish.amount}',
                                 'dish': f'{cartdish.dish.article}'
                                 },
                                status=status.HTTP_200_OK)

        return Response({}, status=status.HTTP_204_NO_CONTENT)


class ShoppingCartViewSet(mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin,
                          mixins.ListModelMixin,
                          viewsets.GenericViewSet,
                          ):

    """
    Вьюсет для просмотра и редакции товаров в корзине.
    PUT запросы запрещены.
    """
    queryset = CartDish.objects.all()
    permission_classes = [AllowAny,]

    def get_queryset(self):
        current_user = self.request.user
        if current_user.is_authenticated:
            cart = ShoppingCart.objects.filter(
                user=current_user.base_profile
                ).select_related(
                    'promocode'
                ).prefetch_related(

                    Prefetch('cartdishes',
                             queryset=CartDish.objects.all(
                             ).select_related(
                                'dish'
                             ).prefetch_related(
                                'dish__translations'
                             )
                             )
                ).first()
            # попробовать свернуть получение вместе с base_profile

            if cart is None:
                cart = ShoppingCart.objects.create(
                    user=current_user.base_profile
                )

            return cart


        return None

    def get_object(self):
        cart = self.get_queryset()
        if cart:
            cartdishes = cart.cartdishes.all()
            cartdish_id = self.kwargs.get('pk')

            return get_object_or_404(cartdishes, pk=cartdish_id)

        return None

    def get_serializer_class(self):
        if self.action == 'list':
            return ShoppingCartSerializer
        elif self.action == 'promocode':
            return ShoppingCartSerializer
        elif self.action == 'partial_update':
            return CartDishSerializer

    def list(self, request, *args, **kwargs):
        """
        Просмотр всех товаров (cartdish) в корзине.
        А так же информации о корзине: сумма, сумма с учетом скидки промокода,
        промокод, кол-во позиций.
        """
        if not request.user.is_authenticated:
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        cart = self.get_queryset()
        if cart:
            cart_serializer = ShoppingCartSerializer(cart)
            return Response(cart_serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Удаление всего блюда (cartdish) из корзины. Корзина пересохраняется.
        id - id cartdish (не id блюда, а именно связи корзина-блюдо(cartdish))
        """
        if not request.user.is_authenticated:
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        super().destroy(request, *args, **kwargs)

        redirect_url = reverse('api:shopping_cart-list')
        return Response({'detail': 'Блюдо успешно удалено.'},
                        status=status.HTTP_200_OK,
                        headers={'Location': redirect_url})

    def update(self, request, *args, **kwargs):
        """
        PUT запрос запрещен.
        """
        if request.method == "PUT":
            return self.http_method_not_allowed(request, *args, **kwargs)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """
        Редактирование кол-ва блюда (cartdish) в корзине. Корзина пересохраняется.
        id - id cartdish (не id блюда, а именно связи корзина-блюдо(cartdish))
        quantity >= 1.
        !!! dish в payload не нужен!!!
        """
        if not request.user.is_authenticated:
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        super().update(request, *args, **kwargs)

        redirect_url = reverse('api:shopping_cart-list')
        return Response({'detail': 'Колличество успешно изменено.'},
                        status=status.HTTP_200_OK,
                        headers={'Location': redirect_url})

    @action(detail=False,
            methods=['delete'])
    def empty_cart(self, request, *args, **kwargs):
        """
        Все товары(cartdishes) в корзине удаляются, сама корзина остается пустой
        и не удаляется.
        """
        if not request.user.is_authenticated:
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        cart = self.get_queryset()

        cart.empty_cart()
        redirect_url = reverse('api:shopping_cart-list')
        return Response({'detail': 'Корзина успешно очищена.'},
                        status=status.HTTP_204_NO_CONTENT,
                        headers={'Location': redirect_url})

    @action(detail=True,
            methods=['get'],
            )
    def plus(self, request, pk=None):
        """
        Добавление одной единицы блюда в кол-во `cartdish` корзины.
        id - id cartdish, которое нужно добавить в `корзину покупок`.

        Args:
            request (WSGIRequest): Объект запроса.
            pk (int):
                id блюда, которое нужно добавить в `корзину покупок`.

        Returns:
            Responce: Статус подтверждающий/отклоняющий действие.
        """
        if not request.user.is_authenticated:
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        cartdish = self.get_object()

        cartdish.quantity += 1
        cartdish.save()

        redirect_url = reverse('api:shopping_cart-list')
        return Response({'detail': 'Блюдо успешно добавлено.'},
                        status=status.HTTP_200_OK,
                        headers={'Location': redirect_url})

    @action(detail=True,
            methods=['get'],
            )
    def minus(self, request, pk=None):
        """
        Удаление одной единицы кол-ва блюда cartdish в корзине.
        id - id cartdish, которое нужно минусовать из корзины покупок.

        Args:
            request (WSGIRequest): Объект запроса.
            pk (int):
                id блюда, которое нужно добавить в `корзину покупок`.

        Returns:
            Responce: Статус подтверждающий/отклоняющий действие.
        """
        if not request.user.is_authenticated:
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        cartdish = self.get_object()

        if cartdish.quantity > 1:
            cartdish.quantity -= 1
            cartdish.save()
        else:
            cartdish.delete()

        redirect_url = reverse('api:shopping_cart-list')
        return Response({'detail': 'Блюдо успешно убрано.'},
                        status=status.HTTP_200_OK,
                        headers={'Location': redirect_url})

    @action(detail=False,
            methods=['post'])
    def promocode(self, request, *args, **kwargs):
        """
        Редактирование промокода (promocode) корзины.
        Для удаления промокода передать { "promocode": null }.
        """
        if not request.user.is_authenticated:
            data = request.data
            promocode = data.get('promocode', None)

            if promocode is None:
                return Response({}, status=status.HTTP_204_NO_CONTENT)

            if Promocode.is_valid(promocode):
                return Response(
                    {"promocode_disc": f"{promocode.discount}",
                     "promocode_code": f"{promocode.promocode}"},
                    status=status.HTTP_200_OK)

            return Response({"No such active promocode."},
                            status=status.HTTP_204_NO_CONTENT)

        cart = self.get_queryset()

        if cart:
            data = request.data
            serializer = self.get_serializer(cart, data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        else:
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        redirect_url = reverse('api:shopping_cart-list')

        if cart.promocode:
            return Response({'detail': 'Promocode is succesfylly added.'},
                            status=status.HTTP_200_OK,
                            headers={'Location': redirect_url})
        else:
            return Response({'detail': 'Promocode успешно удален.'},
                            status=status.HTTP_200_OK,
                            headers={'Location': redirect_url})


class ShopViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет для отображения ресторанов.
    Изменение, создание, удаление ресторанов разрешено только через админку.
    """
    queryset = Restaurant.objects.filter(is_active=True).all()
    serializer_class = RestaurantSerializer
    pagination_class = None


class DeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет для отображения доставки.
    Изменение, создание, удаление разрешено только через админку.
    """
    queryset = Delivery.objects.filter(is_active=True).all()
    serializer_class = DeliverySerializer
    pagination_class = None


class TakeawayOrderViewSet(mixins.CreateModelMixin,
                           mixins.ListModelMixin,
                           viewsets.GenericViewSet,
                           ):
    """
    Вьюсет для заказов самовывозом.
    GET-запрос получает условия самовывоза по городам.
    !!!!! "restaurants" как в api/v1/contacts/
    POST-запрос сохраняет заказ.
    """
    permission_classes = [AllowAny,]

    def get_queryset(self):
        if self.action == 'list':
            queryset = Delivery.get_delivery_conditions(type='takeaway')

        elif self.action == 'create':
            current_user = self.request.user
            if current_user.is_authenticated:
                queryset = Order.objects.filter(
                    user=self.request.user.base_profile).all()

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return TakeawayConditionsSerializer
        elif self.action == 'create':
            return TakeawayOrderWriteSerializer
        elif self.action == 'pre_checkout':
            return TakeawayOrderSerializer

    @action(detail=False,
            methods=['post'])
    def pre_checkout(self, request, *args, **kwargs):
        """
        !!!! Вьюсет для валидации данных и предварительного расчета заказа без его сохранения.
        Ответ либо ошибки валидации данных, либо расчет заказа:
        {
            "amount": 5500.0,
            "promocode_discount": 550.0,
            "delivery_discount": 495.0,
            "total_discount": 1045.0,
            "order_final_amount_with_shipping": 4455.0
        }
        """

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        current_user = self.request.user
        reply_data = {}
        if current_user.is_authenticated:
            cart = get_cart(current_user)
            if cart.promocode is not None:
                promocode = cart.promocode.promocode

            delivery = get_object_or_404(Delivery,
                                         city='Beograd',
                                         type='takeaway')
            if delivery.discount:
                delivery_discount = (
                    Decimal(cart.discounted_amount)
                    * Decimal(delivery.discount) / Decimal(100)
                )
            else:
                delivery_discount = Decimal(0)

            total = (
                Decimal(cart.discounted_amount) - Decimal(delivery_discount)
            )

            reply_data = {}
            reply_data['amount'] = cart.amount
            reply_data['promocode'] = promocode
            reply_data['total_discount'] = (
                cart.discount + delivery_discount)
            reply_data['total'] = {
                "title": "Total amount",
                "total_amount": total
                }

        return Response(reply_data, status=status.HTTP_200_OK)


class DeliveryOrderViewSet(mixins.CreateModelMixin,
                           mixins.ListModelMixin,
                           viewsets.GenericViewSet,
                           ):
    """
    Вьюсет для заказов с доставкой.
    GET-запрос получает условия доставки по городам.
    !!!!! "restaurants" как в api/v1/contacts/
    POST-запрос сохраняет заказ.
    """
    permission_classes = [AllowAny,]

    def get_queryset(self):
        if self.action == 'list':
            queryset = Delivery.get_delivery_conditions(type='delivery')

        elif self.action == 'create':
            current_user = self.request.user
            if current_user.is_authenticated:
                queryset = Order.objects.filter(
                    user=self.request.user.base_profile).all()

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return DeliveryConditionsSerializer
        elif self.action == 'create':
            return DeliveryOrderWriteSerializer
        elif self.action == 'pre_checkout':
            return DeliveryOrderSerializer

    @action(detail=False,
            methods=['post'])
    def pre_checkout(self, request, *args, **kwargs):
        """
        !!!! Вьюсет для валидации данных и предварительного расчета заказа без его сохранения.
        Ответ либо ошибки валидации данных, либо расчет заказа:
        {
            "amount": 5500.0,
            "promocode_discount": 550.0,
            "delivery_discount": 495.0,
            "total_discount": 1045.0,
            "order_final_amount_with_shipping": 4455.0
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        current_user = self.request.user
        if current_user.is_authenticated:
            cart = serializer.initial_data.get('cart')
            city = serializer.initial_data['city']

            delivery = get_object_or_404(Delivery,
                                         city=city,
                                         type='delivery')

            lat=serializer.initial_data.get('lat')
            lon=serializer.initial_data.get('lon')

            delivery_zones = DeliveryZone.objects.filter(city=city).all()
            delivery_cost, delivery_zone = get_delivery_cost_zone(
                delivery_zones,
                discounted_amount=cart.discounted_amount,
                delivery=delivery,
                address=serializer.initial_data.get('recipient_address'),
                lat=serializer.initial_data.get('lat'),
                lon=serializer.initial_data.get('lon'))

            reply_data = get_reply_data(
                cart, delivery, delivery_zone, delivery_cost
            )
        return Response(reply_data, status=status.HTTP_200_OK)


def get_unit_price(request):
    if request.method == 'GET':
        dish_name = request.GET.get('dish_name')
        # Получаем ID блюда из GET-параметров

        activate('ru')
        try:
            # Ищем блюдо по его названию
            from parler.utils import get_active_language_choices

            dish = Dish.objects.filter(
                translations__language_code__in=get_active_language_choices(),
                translations__short_name=dish_name
            )[0]
            # dish = Dish.objects.filter('translations__short_name'==dish_name)[0]
            # dish = Dish.objects.language().get(short_name=dish_name)
            unit_price = dish.final_price  # Получаем актуальную цену блюда
            return JsonResponse({'unit_price': unit_price})
        except Dish.DoesNotExist:
            return JsonResponse({'error': 'Dish not found'}, status=404)
        # Возвращаем ошибку, если блюдо не найдено

    return JsonResponse({'error': 'Invalid request method'}, status=400)
# Возвращаем ошибку, если метод запроса не GET







######-------------------------------------------------------------------------------------------------------#####

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

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from api.permissions import MyIsAdmin

from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.translation import get_language_from_request
from django.db.models import Prefetch
from catalog.models import Dish
from delivery_contacts.models import Delivery, Restaurant, DeliveryZone
from promos.models import PromoNews, Promocode, PrivatPromocode
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
                         UserPromocodeSerializer,
                         ContactsDeliverySerializer,
                         TakeawayOrderSerializer,
                         TakeawayConditionsSerializer,
                         TakeawayOrderWriteSerializer,
                         DeliveryOrderSerializer,
                         DeliveryConditionsSerializer,
                         DeliveryOrderWriteSerializer,
                        )
from decimal import Decimal
from shop.utils import get_reply_data_delivery
from shop.services import get_cart
from rest_framework.exceptions import ValidationError
from django.conf import settings
from delivery_contacts.services import (get_delivery,
                                        get_delivery_cost_zone_by_address)
from delivery_contacts.utils import get_google_api_key
from djoser.views import UserViewSet
from djoser import utils
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken)
from shop.utils import (get_repeat_order_form_data,
                        get_reply_data_takeaway,
                        get_cart_responce_dict)
from shop.services import (get_base_profile_and_shopping_cart,
                           get_cart_detailed,)
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist


logger = logging.getLogger(__name__)

User = get_user_model()


class ContactsDeliveryViewSet(mixins.ListModelMixin,
                              viewsets.GenericViewSet):
    """
    Вьюсет для адреса /contacts.
    Отображает список всех активных ресторанов
    и условия самовывоза во всех городах.
    Доступно только чтение списка
    """
    permission_classes = [AllowAny,]
    serializer_class = ContactsDeliverySerializer

    def list(self, request, *args, **kwargs):
        contacts_delivery_data = []

        # Получаем уникальные города из ресторанов
        cities = set(Restaurant.objects.values_list('city', flat=True))

        for city in cities:
            # Получаем все активные рестораны для данного города
            restaurants = Restaurant.objects.filter(city=city, is_active=True)
            # Получаем условия доставки для данного города
            delivery = Delivery.objects.filter(city=city, is_active=True)

            # Сериализуем данные о ресторанах и усл доставки для данного города
            city_contacts_delivery_data = {
                'city': city,

                'restaurants': RestaurantSerializer(
                    restaurants, many=True).data,

                'delivery': DeliverySerializer(
                    delivery, many=True).data if delivery else None
            }
            contacts_delivery_data.append(city_contacts_delivery_data)

        return Response(contacts_delivery_data, status=status.HTTP_200_OK)


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
        )

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


class MyOrdersViewSet(viewsets.ReadOnlyModelViewSet):
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
                    'orderdishes',
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

    @action(detail=True,
            methods=['post'])   # , 'delete'])
    def repeat(self, request, pk=None):
        """
        Повторение заказа зарегистрированного пользователя.\n
        Корзина очищается и наполняется позициями из выбранного заказа.
        Responce содержит информацию заказа для заполнения формы заказа.
        """
        current_user = request.user

        if not current_user.is_authenticated:
            logger.warning("Reordering is invalid for not authenticated.")
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)

        order = Order.objects.filter(
            user=current_user.base_profile, id=pk).first()
        if order is None:
            logger.warning("No such order ID in user's history.")
            return Response("There's no such order ID in you history.",
                            status=status.HTTP_204_NO_CONTENT)

        base_profile, cart = get_base_profile_and_shopping_cart(
            current_user, validation=True, half_validation=True)

        cart.empty_cart(clean_promocode=False)
        cart_dishes_to_create = [
            CartDish(dish=cartdish.dish, quantity=cartdish.quantity, cart=cart)
            for cartdish in order.orderdishes.all()
            if cartdish.dish.is_active
        ]
        try:
            created_cartdishes = CartDish.objects.bulk_create(
                cart_dishes_to_create)
            for cartdish in created_cartdishes:
                cartdish.save()
        except Exception as e:
            logger.error(f"Failed to repeat the order. Error {e}",
                         exc_info=True)
            return Response("Failed to repeat the order.",
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        repeat_order_form_data = get_repeat_order_form_data(order)
        return Response(repeat_order_form_data,
                        status=status.HTTP_200_OK)


class MyPromocodesViewSet(mixins.ListModelMixin,
                          viewsets.GenericViewSet):
    """
    Вьюсет для просмотра личных промокодов.
    """
    serializer_class = UserPromocodeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PrivatPromocode.objects.filter(
            base_profile=self.request.user.base_profile,
            is_active=True, is_used=False
        )


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
        current_user = request.user

        response_data = {
                'dishes': None,
                'cart': None,
            }
        context = {'request': request}

        if current_user.is_authenticated:
            shopping_cart = get_cart(current_user, validation=False)

            context['extra_kwargs'] = {'cart_items':
                                       shopping_cart.dishes.all()}

            dish_serializer = self.get_serializer(self.get_queryset(),
                                                  many=True,
                                                  context=context,
                                                  )

            items_qty = shopping_cart.items_qty
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
            try:
                dish = get_object_or_404(Dish, article=pk, is_active=True)

            except ObjectDoesNotExist:
                return JsonResponse({"error":
                                     "Unfortunately the requested dish is currently unavailable."},
                                     status=404)

            # cart = get_cart(current_user, validation=False)
            # не исп, т.к. для доб в корз не нужны ни переводы, ни промокоды, ничего

            cart, state = ShoppingCart.objects.get_or_create(
                user=current_user.base_profile,
                complited=False)

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
            return get_cart_detailed(current_user)

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
        current_user = request.user
        if not current_user.is_authenticated:
            data = request.data
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)

            cart_responce_dict = get_cart_responce_dict(
                                    serializer.validated_data, request)
            return Response(cart_responce_dict,
                            status=status.HTTP_200_OK)

        cart = self.get_queryset()

        if cart:
            data = request.data
            serializer = self.get_serializer(cart, data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        else:
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        if cart.promocode:
            return Response({'detail': 'Promocode is succesfylly added.'},
                            status=status.HTTP_200_OK)
        else:
            return Response({'detail': 'Promocode успешно удален.'},
                            status=status.HTTP_200_OK)


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

    def create(self, request, *args, **kwargs):
        if not request.data:
            return Response({'error': 'Request data is missing'},
                            status=status.HTTP_400_BAD_REQUEST)

        delivery = get_delivery(request, 'takeaway')

        context = {'extra_kwargs': {'delivery': delivery},
                   'request': request}

        serializer = self.get_serializer(data=request.data,
                                         context=context)
        if serializer.is_valid(raise_exception=True):
            serializer.save(delivery=delivery)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False,
            methods=['post'])
    def pre_checkout(self, request, *args, **kwargs):
        """
        !!!! Вьюсет для валидации данных и предварительного расчета заказа без его сохранения.
        Ответ либо ошибки валидации данных, либо расчет заказа:
        {
            "amount": 5500.0,
            "promocode": "take10",
            "total_discount": 495.0,
            "total": {
                "title": "order_final_amount_with_shipping",
                "total_amount": 4455.0
        }
        """
        if not request.data:
            return Response({'error': 'Request is missing'},
                            status=status.HTTP_400_BAD_REQUEST)

        delivery = get_delivery(request, 'takeaway')
        context = {'extra_kwargs': {'delivery': delivery},
                   'request': request}

        serializer = self.get_serializer(data=request.data,
                                         context=context)
        serializer.is_valid(raise_exception=True)

        current_user = self.request.user

        if current_user.is_authenticated:
            cart = get_cart(current_user)

            reply_data = get_reply_data_takeaway(delivery,
                                                 cart=cart)

        else:
            orderdishes = serializer.validated_data.get('orderdishes')
            promocode = serializer.validated_data.get('promocode')

            reply_data = get_reply_data_takeaway(delivery,
                                                 orderdishes=orderdishes,
                                                 promocode=promocode)

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

    def create(self, request, *args, **kwargs):
        if not request.data:
            return Response({'error': 'Request data is missing'},
                            status=status.HTTP_400_BAD_REQUEST)

        delivery = get_delivery(request, 'delivery')

        context = {'extra_kwargs': {'delivery': delivery},
                   'request': request}

        serializer = self.get_serializer(data=request.data,
                                         context=context)
        if serializer.is_valid(raise_exception=True):
            serializer.save(delivery=delivery)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False,
            methods=['post'])
    def pre_checkout(self, request, *args, **kwargs):
        """
        !!!! Вьюсет для валидации данных и предварительного расчета заказа без его сохранения.
        Ответ либо ошибки валидации данных, либо расчет заказа:
        {
            "amount": 5500.0,
            "promocode": "take10",
            "total_discount": 1045.0,
            "delivery_cost": 500.0,
            "total": {
                "title: "order_final_amount_with_shipping"
                "total_amount: 4955.0
        }
        """
        if not request.data:
            return Response({'error': 'Request is missing'},
                            status=status.HTTP_400_BAD_REQUEST)

        delivery = get_delivery(request, 'delivery')
        context = {'extra_kwargs': {'delivery': delivery},
                   'request': request}

        serializer = self.get_serializer(data=request.data,
                                         context=context)
        serializer.is_valid(raise_exception=True)

        city = serializer.validated_data.get('city')
        lat = serializer.initial_data.get('lat')
        lon = serializer.initial_data.get('lon')

        current_user = self.request.user
        if current_user.is_authenticated:
            cart = serializer.validated_data.get('cart')

            reply_data = get_reply_data_delivery(delivery, city, lat, lon,
                                                 cart=cart)
        else:
            orderdishes = serializer.validated_data.get('orderdishes')
            promocode = serializer.validated_data.get('promocode')

            reply_data = get_reply_data_delivery(delivery, city, lat, lon,
                                                 orderdishes=orderdishes,
                                                 promocode=promocode)

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


class MyUserViewSet(UserViewSet):

    def perform_update(self, serializer):
        validated_data = serializer.validated_data
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        if instance == request.user:
            utils.logout_user(self.request)
            instance.is_deleted = True
            instance.is_active = False
            instance.base_profile.is_active = False
            logger.debug('web_account проставлена отметка is_deleted = True')
            instance.save()
            instance.base_profile.save(update_fields=['is_active'])
            logger.debug('web_account сохранен')

            active_tokens = OutstandingToken.objects.filter(user=instance)
            # Добавляем каждый активный токен в черный список
            for token in active_tokens:
                BlacklistedToken.objects.create(token=token)

        return Response(status=status.HTTP_204_NO_CONTENT)






# @login_required
# def get_user_data(request):
#     if request.method == 'GET':
#         user_id = request.GET.get('user_id')
#         try:
#             user = BaseProfile.objects.get(id=user_id)
#             user_data = {
#                 'recipient_name': user.first_name,
#                 'recipient_phone': str(user.phone)
#             }
#             return JsonResponse(user_data)
#         except BaseProfile.DoesNotExist:
#             return JsonResponse({'error': 'Пользователь не найден'}, status=404)
#     else:
#         return JsonResponse({'error': 'Метод не разрешен'}, status=405)


class UserDataAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        user_id = request.GET.get('user_id')
        try:
            user = BaseProfile.objects.get(id=user_id)
            # Проверяем, является ли текущий пользователь владельцем
            # запрашиваемого профиля
            if user != request.user.base_profile and not request.user.is_admin:
                return JsonResponse(
                    {'error':
                     'У вас нет прав на доступ к этому профилю'},
                    status=403)

            # Получаем данные пользователя
            my_addresses = UserAddress.objects.filter(base_profile=user)
            address_data = []
            for address in my_addresses:
                address_data.append({
                    'address': str(address),
                    'lat': address.lat,
                    'lon': address.lon
                })

            user_data = {
                'recipient_name': user.first_name,
                'recipient_phone': str(user.phone),
                'my_addresses': address_data
            }
            return JsonResponse(user_data)

        except BaseProfile.DoesNotExist:
            return JsonResponse({'error': 'Пользователь не найден'},
                                status=404)


from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

@csrf_exempt
@require_POST
def calculate_delivery(request):
    # Проверяем, что запрос является AJAX-запросом
    print(request.headers)  # Добавляем отладочное сообщение
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Получаем данные из POST запроса
        data = json.loads(request.body.decode('utf-8'))
        recipient_address = data.get('recipient_address', '')
        discounted_amount = data.get('discounted_amount', '')
        city = data.get('city', '')
        delivery = data.get('delivery', '')

        if recipient_address and discounted_amount and city and delivery:
            discounted_amount = Decimal(discounted_amount)
            delivery = Delivery.objects.get(id=int(delivery))

        # Выполняем расчет доставки (ваша логика расчета)
        try:
            delivery_cost, delivery_zone = (
                get_delivery_cost_zone_by_address(
                    city, discounted_amount, delivery, recipient_address
                )
            )

            # Возвращаем результат в формате JSON
            return JsonResponse({
                'auto_delivery_zone': delivery_zone.name,
                'auto_delivery_cost': delivery_cost,
            })

        except:
            return JsonResponse({
                'error': ("Невозможно произвести расчет, проверьте "
                          "корректность заполненных полей: тип доставки, "
                          "адрес, стоимость заказа, город.")
            })

    else:
        # Если запрос не является AJAX-запросом, возвращаем ошибку
        return JsonResponse({'error': 'This endpoint only accepts AJAX requests'}, status=400)


class GetGoogleAPIKeyAPIView(APIView):
    permission_classes = [MyIsAdmin]


    def get(self, request):

        google_api_key = get_google_api_key()

        return JsonResponse({"GOOGLE_API_KEY": google_api_key})


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

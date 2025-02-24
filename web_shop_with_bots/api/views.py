from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from djoser import utils
from djoser.views import UserViewSet
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from catalog.validators import validator_dish_exists_active
from api.exceptions import CustomHttp400
from catalog.models import Dish
from delivery_contacts.models import Delivery, Restaurant, DeliveryZone
from delivery_contacts.services import (get_delivery,
                                        get_delivery_cost_zone_by_address,
                                        get_delivery_cost_zone,
                                        )
from delivery_contacts.utils import (get_google_api_key,
                                     parce_coordinates, get_address_comment)
from promos.models import PrivatPromocode, PromoNews
from shop.models import Order, OrderDish, Discount, current_cash_disc_status
from shop.services import (get_base_profile_and_shopping_cart, get_cart,
                           base_profile_first_order, get_cash_discount)
from .services import (get_promoc_resp_dict, get_repeat_order_form_data,
                       get_reply_data_delivery, get_reply_data_takeaway)
from shop.validators import validate_user_order_exists
from users.models import BaseProfile, UserAddress

from .filters import CategoryFilter
import logging.config
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.translation import get_language_from_request
import json
from tm_bot.models import get_status_tmbot, OrdersBot, get_bot
from django.views.decorators.cache import cache_page
import api.serializers as srlz
import logging
from django.shortcuts import render
from django.conf import settings


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
    serializer_class = srlz.ContactsDeliverySerializer

    @method_decorator(cache_page(settings.CACHE_TIME))
    def list(self, request, *args, **kwargs):
        logger.info(f'contacts/ REQUEST: {self.request.data} '
                    f'USER:{self.request.user}')
        contacts_delivery_data = []

        # Получаем уникальные города из ресторанов
        cities = set(Restaurant.objects.filter(
                        is_active=True).values_list('city', flat=True))
        # Получаем все активные рестораны для данного города
        restaurants_qs = Restaurant.objects.filter(is_active=True)
        # Получаем условия доставки для данного города
        delivery_qs = Delivery.objects.filter(is_active=True)
        bots_qs = OrdersBot.objects.filter(is_active=True)

        for city in cities:
            # Получаем все активные рестораны для данного города
            restaurants = restaurants_qs.filter(city=city)
            # Получаем условия доставки для данного города
            delivery = delivery_qs.filter(city=city)
            bots = bots_qs.filter(city=city)

            # Сериализуем данные о ресторанах и усл доставки для данного города
            city_contacts_delivery_data = {
                'city': city,

                'restaurants': srlz.RestaurantSerializer(
                    restaurants, many=True).data if restaurants else None,

                'delivery': srlz.DeliverySerializer(
                    delivery, many=True).data if delivery else None,

                'bots': srlz.OrdersBotSerializer(
                    bots, many=True).data if bots else None
            }
            contacts_delivery_data.append(city_contacts_delivery_data)
        cash_discount_data = {'cash_discount': current_cash_disc_status()}
        contacts_delivery_data.append(cash_discount_data)

        return Response(contacts_delivery_data, status=status.HTTP_200_OK)


class DeliveryZonesViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет модели DeliveryZones доступен только для чтения.
    Отбираются только зоны is_active=True.
    """
    queryset = DeliveryZone.objects.all()
    serializer_class = srlz.DeliveryZonesSerializer
    permission_classes = [AllowAny,]

    @method_decorator(cache_page(settings.CACHE_TIME))
    def list(self, request, *args, **kwargs):
        delivery_zones = DeliveryZone.objects.exclude(city__isnull=True)
        cities = set(delivery_zones.values_list('city', flat=True))
        city_delivery_zones = {}

        # Группировка по городам
        for city in cities:
            city_del_zones = delivery_zones.filter(city=city)
            city_data = {}

            # Группировка по зонам внутри города
            for zone in city_del_zones:
                serializer = self.get_serializer(zone)
                zone_data = serializer.data.get(city)
                if zone_data:
                    city_data.update(zone_data)

            city_delivery_zones[city] = city_data

        return Response(city_delivery_zones, status=status.HTTP_200_OK)


class MyAddressViewSet(mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.CreateModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.DestroyModelMixin,
                       viewsets.GenericViewSet):
    """
    Вьюсет модели UserAddresses для просмотра сохраненных адресов пользователя.
    """
    serializer_class = srlz.UserAddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserAddress.objects.filter(
            base_profile=self.request.user.base_profile
        )

    def get_object(self):
        address_pk = self.kwargs.get('pk')
        try:
            # Пытаемся найти адрес
            address = self.get_queryset().get(id=int(address_pk))
            return address
        except UserAddress.DoesNotExist:
            # Если адрес с указанным идентификатором не найден,
            # возвращаем ошибку
            raise CustomHttp400("Such address is unavailable.", code='invalid')

    def perform_create(self, serializer):
        logger.info(f'me/my_addresses/ CREATE REQUEST: {self.request.data} '
                    f'USER:{self.request.user}')
        serializer.save(base_profile=self.request.user.base_profile)

    def perform_update(self, serializer):
        logger.info(f'me/my_addresses/ UPDATE REQUEST: {self.request.data} '
                    f'USER:{self.request.user}')
        serializer.save()


class ClientAddressesViewSet(mixins.ListModelMixin,
                             viewsets.GenericViewSet):
    """
    Вьюсет для всех пользователей для получения сохраненных адресов клиента.
    """
    serializer_class = srlz.UserAddressSerializer
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
    queryset = PromoNews.objects.filter(
                    is_active=True).all().prefetch_related('translations')
    serializer_class = srlz.PromoNewsSerializer
    permission_classes = [AllowAny,]


class MyOrdersViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет модели Orders для просмотра истории заказов.
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return srlz.UserOrdersSerializer
        elif self.action == 'repeat':
            return srlz.RepeatOrderSerializer

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
        Responce содержит информацию заказа для заполнения формы заказа.
        В запросе необходимо передавать ID заказа.
        """
        current_user = request.user

        if not current_user.is_authenticated:
            logger.warning("Reordering is invalid for not authenticated.")
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)

        logger.info(f'me/my_orders/{id}/repeat/ REQUEST: {self.request.data} '
                    f'USER:{self.request.user}')

        order = Order.objects.filter(
            user=current_user.base_profile, id=pk).first()
        validate_user_order_exists(order)

        # cart_dishes_to_create = [
        #     CartDish(dish=cartdish.dish, quantity=cartdish.quantity, cart=cart)
        #     for cartdish in order.orderdishes.all()
        #     if cartdish.dish.is_active
        # ]
        # try:
        #     created_cartdishes = CartDish.objects.bulk_create(
        #         cart_dishes_to_create)
        #     for cartdish in created_cartdishes:
        #         cartdish.save()
        # except Exception as e:
        #     logger.error(f"Failed to repeat the order. Error {e}",
        #                  exc_info=True)
        #     return Response("Failed to repeat the order.",
        #                     status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        serialized_data = self.get_serializer(order).data
        logger.info(f'me/my_orders/{id}/repeat/ serialized_data: {serialized_data}')

        return Response(serialized_data, status=status.HTTP_201_CREATED)


class MyPromocodesViewSet(mixins.ListModelMixin,
                          viewsets.GenericViewSet):
    """
    Вьюсет для просмотра личных промокодов.
    """
    serializer_class = srlz.UserPromocodeSerializer
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
    serializer_class = srlz.DishMenuSerializer
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
    ).order_by('category__priority', 'priority')

    http_method_names = ['get', 'post']

    @method_decorator(cache_page(settings.CACHE_TIME))
    def list(self, request, *args, **kwargs):

        response_data = {
                'dishes': None,
                'cart': None,
            }
        context = {'request': request}
        # current_user = request.user
        # if current_user.is_authenticated:
        #     shopping_cart = get_cart(current_user, validation=False)

        #     context['extra_kwargs'] = {'cart_items':
        #                                shopping_cart.dishes.all()}

        #     dish_serializer = self.get_serializer(self.get_queryset(),
        #                                           many=True,
        #                                           context=context,
        #                                           )

        #     items_qty = shopping_cart.items_qty
        #     response_data['cart'] = {'items_qty': items_qty}
        # else:


        qs = self.get_queryset()
        unique_qs = []
        for dish in qs:
            if dish not in unique_qs:
                unique_qs.append(dish)

        dish_serializer = self.get_serializer(unique_qs,
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
            methods=['post'])
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
        # method = request.META['REQUEST_METHOD']
        validator_dish_exists_active(pk)

        # dish = get_dish_validate_exists_active(pk)
        # current_user = request.user
        # if current_user.is_authenticated:
        #     # cart = get_cart(current_user, validation=False)
        #     # не исп, т.к. для доб в корз не нужны ни переводы, ни промокоды, ничего

        #     cart, state = ShoppingCart.objects.get_or_create(
        #         user=current_user.base_profile,
        #         complited=False)

        #     if method == 'POST':
        #         cartdish, created = CartDish.objects.get_or_create(
        #             cart=cart, dish=dish)
        #         if not created:
        #             cartdish.quantity += 1
        #             cartdish.save(update_fields=['quantity', 'amount'])

        #         return Response({'cartdish': f'{cartdish.id}',
        #                          'quantity': f'{cartdish.quantity}',
        #                          'amount': f'{cartdish.amount}',
        #                          'dish': f'{cartdish.dish.article}'
        #                          },
        #                         status=status.HTTP_200_OK)

        return Response({"message":
                         "Dish is successfully added into the cart."},
                        status=status.HTTP_204_NO_CONTENT)


class ShoppingCartViewSet(mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin,
                          mixins.ListModelMixin,
                          viewsets.GenericViewSet,
                          ):

    """
    Вьюсет для просмотра и редакции товаров в корзине.
    PUT запросы запрещены.
    """
    # queryset = CartDish.objects.all()
    permission_classes = [AllowAny,]

    def get_queryset(self):
        return None
    #     current_user = self.request.user

    #     if current_user.is_authenticated:
    #         # return get_cart_detailed(current_user)

    #     return None

    # def get_object(self):
    #     cart = self.get_queryset()
    #     if cart:
    #         cartdishes = cart.cartdishes.all()
    #         cartdish_id = self.kwargs.get('pk')

    #         return get_object_or_404(cartdishes, pk=cartdish_id)

    #     return None

    def get_serializer_class(self):
        if self.action == 'list':
            return srlz.ShoppingCartSerializer
    #     elif self.action == 'promocode':
    #         return srlz.ShoppingCartSerializer
    #     elif self.action == 'partial_update':
    #         return srlz.CartDishSerializer

    def list(self, request, *args, **kwargs):
        """
        Просмотр всех товаров (cartdish) в корзине.
        А так же информации о корзине: сумма, сумма с учетом скидки промокода,
        промокод, кол-во позиций.
        """
        data = request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        current_user = self.request.user
        if current_user.is_authenticated:
            reply = {"first_order": False,
                     "discount": None}

            if base_profile_first_order(current_user):
                discount = Discount.objects.filter(
                    type='1', is_active=True).first()
                if discount:
                    reply = {"first_order": True,
                             "discount": discount.show_discount()}

            return Response(reply,
                            status=status.HTTP_200_OK)

        return Response({}, status=status.HTTP_200_OK)

        # if not request.user.is_authenticated:
        #     data = request.data
        #     serializer = self.get_serializer(data=data)
        #     serializer.is_valid(raise_exception=True)

        #     cart_responce_dict = get_cart_responce_dict(
        #                             serializer.validated_data, request)
        #     return Response(cart_responce_dict,
        #                     status=status.HTTP_200_OK)

        # cart = self.get_queryset()
        # if cart:
        #     cart_serializer = srlz.ShoppingCartSerializer(cart)
        #     return Response(cart_serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Удаление всего блюда (cartdish) из корзины. Корзина пересохраняется.
        id - id cartdish (не id блюда, а именно связи корзина-блюдо(cartdish))
        """
        # if not request.user.is_authenticated:
        #     return Response({}, status=status.HTTP_204_NO_CONTENT)

        # super().destroy(request, *args, **kwargs)

        # redirect_url = reverse('api:shopping_cart-list')
        # return Response({'detail': 'Блюдо успешно удалено.'},
        #                 status=status.HTTP_200_OK,
        #                 headers={'Location': redirect_url})
        return Response({}, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """
        PUT запрос запрещен.
        """
        if request.method == "PUT":
            return self.http_method_not_allowed(request, *args, **kwargs)
        # return super().update(request, *args, **kwargs)
        return Response({}, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        """
        Редактирование кол-ва блюда (cartdish) в корзине. Корзина пересохраняется.
        id - id cartdish (не id блюда, а именно связи корзина-блюдо(cartdish))
        quantity >= 1.
        !!! dish в payload не нужен!!!
        """
        # if not request.user.is_authenticated:
        #     return Response({}, status=status.HTTP_204_NO_CONTENT)

        # super().update(request, *args, **kwargs)

        # redirect_url = reverse('api:shopping_cart-list')
        # return Response({'detail': 'Колличество успешно изменено.'},
        #                 status=status.HTTP_200_OK,
        #                 headers={'Location': redirect_url})
        return Response({}, status=status.HTTP_200_OK)

    @action(detail=False,
            methods=['delete'])
    def empty_cart(self, request, *args, **kwargs):
        """
        Все товары(cartdishes) в корзине удаляются, сама корзина остается пустой
        и не удаляется.
        """
        # if not request.user.is_authenticated:
        #     return Response({}, status=status.HTTP_204_NO_CONTENT)

        # cart = self.get_queryset()

        # cart.empty_cart()
        # redirect_url = reverse('api:shopping_cart-list')
        # return Response({'detail': 'Корзина успешно очищена.'},
        #                 status=status.HTTP_204_NO_CONTENT,
        #                 headers={'Location': redirect_url})
        return Response({}, status=status.HTTP_200_OK)

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
        # if not request.user.is_authenticated:
        #     return Response({}, status=status.HTTP_204_NO_CONTENT)

        # cartdish = self.get_object()

        # cartdish.quantity += 1
        # cartdish.save()

        # redirect_url = reverse('api:shopping_cart-list')
        # return Response({'detail': 'Блюдо успешно добавлено.'},
        #                 status=status.HTTP_200_OK,
        #                 headers={'Location': redirect_url})
        return Response({}, status=status.HTTP_200_OK)

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
        # if not request.user.is_authenticated:
        #     return Response({}, status=status.HTTP_204_NO_CONTENT)

        # cartdish = self.get_object()

        # if cartdish.quantity > 1:
        #     cartdish.quantity -= 1
        #     cartdish.save()
        # else:
        #     cartdish.delete()

        # redirect_url = reverse('api:shopping_cart-list')
        # return Response({'detail': 'Блюдо успешно убрано.'},
        #                 status=status.HTTP_200_OK,
        #                 headers={'Location': redirect_url})
        return Response({}, status=status.HTTP_200_OK)


class ShopViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет для отображения ресторанов.
    Изменение, создание, удаление ресторанов разрешено только через админку.
    """
    queryset = Restaurant.objects.filter(is_active=True).all()
    serializer_class = srlz.RestaurantSerializer
    pagination_class = None


class DeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет для отображения доставки.
    Изменение, создание, удаление разрешено только через админку.
    """
    queryset = Delivery.objects.filter(is_active=True).all()
    serializer_class = srlz.DeliverySerializer
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
            return srlz.TakeawayConditionsSerializer
        elif self.action == 'create':
            return srlz.TakeawayOrderWriteSerializer
        elif self.action == 'pre_checkout':
            return srlz.TakeawayOrderSerializer
        elif self.action == 'promocode':
            return srlz.BaseOrderSerializer

    def create(self, request, *args, **kwargs):
        if not request.data:
            return Response({'error': 'Request data is missing'},
                            status=status.HTTP_400_BAD_REQUEST)
        logger.info(f'/create_order_takeaway/ REQUEST: {request.data} '
                    f'USER:{request.user}')
        delivery = get_delivery(request, 'takeaway')

        context = {'extra_kwargs': {'delivery': delivery},
                   'request': request}

        serializer = self.get_serializer(data=request.data,
                                         context=context)
        serializer.is_valid(raise_exception=True)
        logger.info(f'/create_order_takeaway/ '
                    f'SERIALIZER_VALIDATED_DATA: {serializer.validated_data}')
        instance = serializer.save()

        # Преобразуем сохраненный объект в словарь
        serialized_data = self.get_serializer(instance).data
        logger.info(f'/create_order_takeaway/ REPLY_DATA: {serialized_data}')
        return Response(serialized_data, status=status.HTTP_201_CREATED)

    @action(detail=False,
            methods=['post'])
    def pre_checkout(self, request, *args, **kwargs):
        """
        Предварительный расчет заказа САМОВЫВОЗ: валидация данных,
        расчет без сохранения.
        Ответ либо ошибки валидации данных, либо расчет заказа:
        {
            "amount": 5500.0,
            "promocode": "percnt10",
            "total_discount": 495.0,
            "total": {
                "title": "order_final_amount_with_shipping",
                "total_amount": 4455.0
        }
        """
        logger.info(f'/create_order_takeaway/pre_checkout/'
                    f'REQUEST: {request.data} '
                    f'USER:{request.user}')
        if not request.data:
            return Response({'error': 'Request is missing'},
                            status=status.HTTP_400_BAD_REQUEST)

        delivery = get_delivery(request, 'takeaway')
        context = {'extra_kwargs': {'delivery': delivery},
                   'request': request}

        serializer = self.get_serializer(data=request.data,
                                         context=context)
        serializer.is_valid(raise_exception=True)
        logger.info(f'/create_order_takeaway/pre_checkout/ '
                    f'SERIALIZER_VALIDATED_DATA: {serializer.validated_data}')
        # current_user = self.request.user
        # if current_user.is_authenticated:
        #     cart = get_cart(current_user)

        #     reply_data = get_reply_data_takeaway(delivery,
        #                                          cart=cart,
        #                                          request=request)

        # else:

        reply_data = serializer.get_reply_data_takeaway()

        # orderdishes = serializer.validated_data.get('orderdishes')
        # promocode = serializer.validated_data.get('promocode')

        # reply_data = get_reply_data_takeaway(delivery,
        #                                      orderdishes=orderdishes,
        #                                      promocode=promocode,
        #                                      request=request)
        logger.info(f'/create_order_takeaway/pre_checkout/'
                    f' REPLY_DATA: {reply_data}')
        return Response(reply_data, status=status.HTTP_200_OK)

    @action(detail=False,
            methods=['post'])
    def promocode(self, request, *args, **kwargs):
        """
        Редактирование промокода (promocode) корзины.
        Для удаления промокода передать { "promocode": null }.
        """
        if not request.data:
            return Response({'error': 'Request is missing'},
                            status=status.HTTP_400_BAD_REQUEST)
        logger.info(f'/create_order_takeaway/promocode/ '
                    f'REQUEST: {request.data} '
                    f'USER:{request.user}')
        delivery = get_delivery(request, 'takeaway')
        context = {'extra_kwargs': {'delivery': delivery},
                   'request': request}

        serializer = self.get_serializer(data=request.data,
                                         context=context)
        serializer.is_valid(raise_exception=True)
        logger.info(f'/create_order_takeaway/promocode/ '
                    f'SERIALIZER_VALIDATED_DATA: {serializer.validated_data} '
                    f'USER:{request.user}')
        promoc_resp_dict = get_promoc_resp_dict(
                            serializer.validated_data, request)
        logger.info(f'/create_order_takeaway/promocode/ '
                    f'REPLY_DATA: {promoc_resp_dict} '
                    f'USER:{request.user}')
        return Response(promoc_resp_dict,
                        status=status.HTTP_200_OK)


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
            return srlz.DeliveryConditionsSerializer
        elif self.action == 'create':
            return srlz.DeliveryOrderWriteSerializer
        elif self.action == 'pre_checkout':
            return srlz.DeliveryOrderSerializer
        elif self.action == 'promocode':
            return srlz.BaseOrderSerializer

    def create(self, request, *args, **kwargs):
        if not request.data:
            return Response({'error': 'Request data is missing'},
                            status=status.HTTP_400_BAD_REQUEST)
        logger.info(f'/create_order_delivery/ REQUEST: {request.data} '
                    f'USER:{request.user}')
        delivery = get_delivery(request, 'delivery')

        context = {'extra_kwargs': {'delivery': delivery},
                   'request': request}

        serializer = self.get_serializer(data=request.data,
                                         context=context)
        serializer.is_valid(raise_exception=True)
        logger.info(f'/create_order_delivery/ '
                    f'SERIALIZER_VALIDATED_DATA: {serializer.validated_data}')
        instance = serializer.save()

        # Преобразуем сохраненный объект в словарь
        serialized_data = self.get_serializer(instance).data
        logger.info(f'/create_order_delivery/ REPLY_DATA: {serialized_data}')
        return Response(serialized_data, status=status.HTTP_201_CREATED)

    @action(detail=False,
            methods=['post'])
    def pre_checkout(self, request, *args, **kwargs):
        """
        Предварительный расчет заказа ДОСТАВКА: валидация данных,
        расчет без сохранения.
        Ответ либо ошибки валидации данных, либо расчет заказа:
        {
            "amount": 5500.0,
            "promocode": "percnt10",
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

        logger.info(f'/create_order_delivery/pre_checkout/ '
                    f'REQUEST: {request.data} USER:{request.user}')

        delivery = get_delivery(request, 'delivery')
        context = {'extra_kwargs': {'delivery': delivery},
                   'request': request}

        serializer = self.get_serializer(data=request.data,
                                         context=context)
        serializer.is_valid(raise_exception=True)

        logger.info(f'/create_order_delivery/pre_checkout/ '
                    f'SERIALIZER_VALIDATED_DATA: {serializer.validated_data}')

        # city = serializer.validated_data.get('city')
        # lat, lon = parce_coordinates(
        #     serializer.initial_data.get('coordinates'))
        # orderdishes = serializer.validated_data.get('orderdishes')
        # promocode = serializer.validated_data.get('promocode')
        # payment_type = serializer.validated_data.get('payment_type')
        # language = serializer.validated_data.get('language')

        # reply_data = get_reply_data_delivery(delivery, city, lat, lon,
        #                                      orderdishes=orderdishes,
        #                                      promocode=promocode,
        #                                      payment_type=payment_type,
        #                                      language=language,
        #                                      request=request)

        reply_data = serializer.get_reply_data_delivery()

        logger.info(f'/create_order_delivery/pre_checkout/ '
                    f'REPLY_DATA: {reply_data}')

        return Response(reply_data, status=status.HTTP_200_OK)

    @action(detail=False,
            methods=['post'])
    def promocode(self, request, *args, **kwargs):
        """
        Редактирование промокода (promocode) корзины.
        Для удаления промокода передать { "promocode": null }.
        """
        if not request.data:
            return Response({'error': 'Request is missing'},
                            status=status.HTTP_400_BAD_REQUEST)

        delivery = get_delivery(request, 'delivery')
        context = {'extra_kwargs': {'delivery': delivery},
                   'request': request}
        logger.info(f'/create_order_delivery/promocode/ '
                    f'REQUEST: {request.data} USER:{request.user}')
        serializer = self.get_serializer(data=request.data,
                                         context=context)
        serializer.is_valid(raise_exception=True)
        logger.info(f'/create_order_delivery/promocode/ '
                    f'SERIALIZER_VALIDATED_DATA: {serializer.validated_data}')
        promoc_resp_dict = get_promoc_resp_dict(
                            serializer.validated_data, request)
        logger.info(f'/create_order_delivery/promocode/ '
                    f'REPLY_DATA: {promoc_resp_dict}')
        return Response(promoc_resp_dict,
                        status=status.HTTP_200_OK)


class MyUserViewSet(UserViewSet):

    def update(self, request, *args, **kwargs):
        logger.info(f'/profile/ UPDATE REQUEST RECEIVED: {self.request.data} '
                    f'USER: {self.request.user}')

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)

        serializer.is_valid(raise_exception=True)
        logger.info(f'/profile/ UPDATE'
                    f'SERIALIZER_VALIDATED_DATA: {serializer.validated_data}')
        self.perform_update(serializer)

        logger.info(f'/profile/ UPDATE successfully saved.')
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        logger.info(f'profile/ DELETE REQUEST: {self.request.data} '
                    f'USER:{self.request.user}')

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        if instance == request.user:
            utils.logout_user(self.request)
            instance.is_deleted = True
            instance.is_active = False
            instance.base_profile.is_active = False
            logger.info(
                f'web_account {instance} '
                f'проставлена отметка is_deleted = True')
            instance.save()
            instance.base_profile.save(update_fields=['is_active'])
            logger.info(f'web_account {instance} сохранен')

            active_tokens = OutstandingToken.objects.filter(user=instance)
            # Добавляем каждый активный токен в черный список
            for token in active_tokens:
                # BlacklistedToken.objects.create(token=token)
                token_obj = RefreshToken(token.token)
                token_obj.blacklist()

        return Response(status=status.HTTP_204_NO_CONTENT)


class UserDataAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logger.info(f'/get_user_data/ '
                    f'REQUEST: {request} USER:{request.user}')
        user_id = request.GET.get('user_id')
        try:
            user = BaseProfile.objects.select_related(
                'messenger_account'
            ).prefetch_related(
                'addresses'
            ).get(id=int(user_id))
            # Проверяем, является ли текущий пользователь владельцем
            # запрашиваемого профиля или админом
            if user != request.user.base_profile and not request.user.is_admin:
                logger.info(f'У вас нет прав на доступ к этому профилю')
                return JsonResponse(
                    {'error':
                     'У вас нет прав на доступ к этому профилю'},
                    status=403)

            my_addresses = user.addresses.all()
            my_addresses_data = []
            if my_addresses:
                for address in my_addresses:
                    address_comment = get_address_comment(address)
                    my_addresses_data.append(
                        {
                            'id': address.id,
                            'address': address.address,
                            'coordinates': address.coordinates,
                            'address_comment': address_comment,
                        }
                    )

            if user.messenger_account:
                msgr_link = user.messenger_account.msngr_link
            else:
                msgr_link = None

            #orders_data = user.get_orders_data()
            orders_data = None

            user_data = {
                'recipient_name': user.first_name,
                'recipient_phone': str(user.phone),
                'language': user.base_language,
                'msgr_link': msgr_link,
                'orders_data': orders_data,
                'my_addresses': my_addresses_data
            }
            logger.info(f'/get_user_data/ '
                        f'user_data: {user_data}')
            return JsonResponse(user_data)

        except BaseProfile.DoesNotExist:
            logger.info(f'/get_user_data/ '
                        f'User is not found.')
            return JsonResponse({'error': _("User is not found.")},
                                status=404)


from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@require_POST
def calculate_delivery(request):
    request_body = request.body
    decoded_string = request_body.decode('utf-8')
    logger.info(f'/calculate_delivery/ '
                f'REQUEST: {decoded_string} USER:{request.user}')
    if request.method == 'POST':

        # Проверяем, что запрос является AJAX-запросом
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Если запрос не является AJAX-запросом, возвращаем ошибку
            return JsonResponse({'error':
                                _('This endpoint only accepts AJAX requests.')},
                                status=400)

    # Получаем данные из POST запроса
    data = json.loads(request.body.decode('utf-8'))
    recipient_address = data.get('recipient_address', '')
    amount = data.get('amount', '')
    city = data.get('city', '')
    delivery = data.get('delivery', '')
    coordinates = data.get('coordinates', '')

    if (recipient_address and amount and city and delivery
        and (coordinates not in ['undefined'])):
        amount = Decimal(amount)
        delivery = Delivery.objects.get(id=int(delivery))
        lat, lon = parce_coordinates(coordinates)

        # Выполняем расчет доставки (ваша логика расчета)
        try:
            delivery_cost, delivery_zone = (
                get_delivery_cost_zone(
                    city, amount, delivery,
                    lat, lon)   # free_delivery):
            )

            # вариант без координат
            # delivery_cost, delivery_zone = (
            #     get_delivery_cost_zone_by_address(
            #         city, discounted_amount, delivery, recipient_address
            #     )
            # )

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
        return JsonResponse({
                'auto_delivery_zone': 'уточнить',
                'auto_delivery_cost': '-',
            })


@method_decorator(staff_member_required, name='dispatch')
class GetGoogleAPIKeyAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        logger.info(f'/get_google_api_key/ '
                    f'REQUEST: {request} USER:{request.user}')
        google_api_key = get_google_api_key()
        return Response({"GOOGLE_API_KEY": google_api_key})


@method_decorator(staff_member_required, name='dispatch')
class GetDiscountsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        logger.info(f'/get_discounts/ '
                    f'REQUEST: {request} USER:{request.user}')
        discounts = {}
        discounts_list = Discount.objects.all()
        for discount in discounts_list:
            discounts.update({discount.pk: {
                                'is_active': discount.is_active,
                                'discount_am': discount.discount_am,
                                'discount_perc': discount.discount_perc,
                                'title': discount.title_rus
                                }
                              })

        return Response(discounts)


def get_dish_price(request):
    logger.info(f'/get_dish_price/ '
                f'REQUEST: {request} USER:{request.user}')
    if request.method == 'GET':
        # Проверяем, что запрос является AJAX-запросом
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Получаем данные из GET запроса
            dish_id = request.GET.get('dish_id', None)

            if dish_id is not None:
                try:
                    dish = Dish.objects.get(article=dish_id,
                                            is_active=True)
                    unit_price = dish.final_price
                    final_price_p1 = dish.final_price_p1
                    final_price_p2 = dish.final_price_p2
                    # Получаем актуальную цену блюда
                    return JsonResponse({'price': unit_price,
                                         'price_p1': final_price_p1,
                                         'price_p2': final_price_p2
                                         })
                except Dish.DoesNotExist:
                    return JsonResponse({'error': 'Dish not found'},
                                        status=404)
            else:
                return JsonResponse({'error': 'Dish ID is not provided'},
                                    status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=400)


@csrf_exempt
@require_POST
def save_bot_order(request):
    if request.method == 'POST':
        request_body = request.body
        decoded_string = request_body.decode('utf-8')
        logger.info(f'/save_bot_order/ REQUEST: {decoded_string}')

        # Получаем данные из POST запроса
        logger.info(f'/save_bot_order/ REQUEST: {request.POST}')

        bot = get_bot(data=request.POST)
        id = request.POST.get("id")
        status = get_status_tmbot(request.POST.get("statusName"))
        order = Order.objects.filter(source='3',
                                     city=bot.city,
                                     source_id=id).first()

        if order:
            if status is None or status == order.status:
                logger.info(f'Bot order #{order.source_id}/ '
                            'status changed in bot, but not in ORM.')
                return JsonResponse({}, status=200)

            order.status = status
            order.save()
            logger.info(f'Bot order #{order.source_id}/ '
                        f'ORM order #{order.id} '
                        f'updated status {order.status}.')
            return JsonResponse({}, status=200)

        context = {'extra_kwargs': {'bot': bot},
                   'request': request}
        serializer = srlz.BotOrderSerializer(data=request.POST,
                                             context=context)
        serializer.is_valid()
        return JsonResponse({}, status=201)

    logger.error(f"Bot order #{request} isn't saved. ",
                 "Request method is not 'POST'")

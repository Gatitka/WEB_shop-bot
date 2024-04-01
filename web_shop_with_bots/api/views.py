import logging
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.http import JsonResponse
from django.utils.translation import activate
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
from api.permissions import MyIsAdmin
from catalog.models import Dish
from catalog.validators import validator_dish_exists_active
from delivery_contacts.models import Delivery, Restaurant
from delivery_contacts.services import (get_delivery,
                                        get_delivery_cost_zone_by_address)
from delivery_contacts.utils import get_google_api_key
from promos.models import PrivatPromocode, PromoNews
from shop.models import CartDish, Order, OrderDish, Discount
from shop.services import (get_base_profile_and_shopping_cart, get_cart,
                           base_profile_first_order)
from .services import (get_promoc_resp_dict, get_repeat_order_form_data,
                       get_reply_data_delivery, get_reply_data_takeaway)
from users.models import BaseProfile, UserAddress

from . import serializers as srlz
from .filters import CategoryFilter

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

                'restaurants': srlz.RestaurantSerializer(
                    restaurants, many=True).data,

                'delivery': srlz.DeliverySerializer(
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
        serializer.save(base_profile=self.request.user.base_profile)

    def perform_update(self, serializer):
        serializer.save(base_profile=self.request.user.base_profile)


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
    serializer_class = srlz.UserOrdersSerializer
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
            return Response(_("There's no such order ID in you orders history."),
                            status=status.HTTP_204_NO_CONTENT)

        base_profile, cart = get_base_profile_and_shopping_cart(
            current_user, validation=True, half_validation=True)

        cart.empty_cart()
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
            if base_profile_first_order(current_user):
                discount = Discount.orders.get(type='первый заказ')
                reply = {"first_order": True,
                         "discount": discount.show_discount()}

            else:
                reply = {"first_order": False,
                         "discount": None}

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
        if not request.data:
            return Response({'error': 'Request is missing'},
                            status=status.HTTP_400_BAD_REQUEST)

        delivery = get_delivery(request, 'takeaway')
        context = {'extra_kwargs': {'delivery': delivery},
                   'request': request}

        serializer = self.get_serializer(data=request.data,
                                         context=context)
        serializer.is_valid(raise_exception=True)

        # current_user = self.request.user
        # if current_user.is_authenticated:
        #     cart = get_cart(current_user)

        #     reply_data = get_reply_data_takeaway(delivery,
        #                                          cart=cart,
        #                                          request=request)

        # else:
        orderdishes = serializer.validated_data.get('orderdishes')
        promocode = serializer.validated_data.get('promocode')

        reply_data = get_reply_data_takeaway(delivery,
                                             orderdishes=orderdishes,
                                             promocode=promocode,
                                             request=request)

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

        delivery = get_delivery(request, 'takeaway')
        context = {'extra_kwargs': {'delivery': delivery},
                   'request': request}

        serializer = self.get_serializer(data=request.data,
                                         context=context)
        serializer.is_valid(raise_exception=True)

        promoc_resp_dict = get_promoc_resp_dict(
                            serializer.validated_data, request)
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
                                                 cart=cart, request=request)
        else:
            orderdishes = serializer.validated_data.get('orderdishes')
            promocode = serializer.validated_data.get('promocode')

            reply_data = get_reply_data_delivery(delivery, city, lat, lon,
                                                 orderdishes=orderdishes,
                                                 promocode=promocode,
                                                 request=request)

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

        serializer = self.get_serializer(data=request.data,
                                         context=context)
        serializer.is_valid(raise_exception=True)

        promoc_resp_dict = get_promoc_resp_dict(
                            serializer.validated_data, request)
        return Response(promoc_resp_dict,
                        status=status.HTTP_200_OK)


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
                # BlacklistedToken.objects.create(token=token)
                token_obj = RefreshToken(token.token)
                token_obj.blacklist()

        return Response(status=status.HTTP_204_NO_CONTENT)


class UserDataAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        user_id = request.GET.get('user_id')
        try:
            user = BaseProfile.objects.get(id=user_id)
            # Проверяем, является ли текущий пользователь владельцем
            # запрашиваемого профиля или админом
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
            return JsonResponse({'error': _("User is not found.")},
                                status=404)


import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


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
        return JsonResponse({'error': _('This endpoint only accepts AJAX requests.')}, status=400)


class GetGoogleAPIKeyAPIView(APIView):
    permission_classes = [MyIsAdmin]


    def get(self, request):

        google_api_key = get_google_api_key()

        return JsonResponse({"GOOGLE_API_KEY": google_api_key})

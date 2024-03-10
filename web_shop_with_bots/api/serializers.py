
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import EmailValidator
from django.db.models import F, QuerySet
from djoser.compat import get_user_email, get_user_email_field_name
from parler_rest.fields import \
    TranslatedFieldsField  # для переводов текста parler
from parler_rest.serializers import \
    TranslatableModelSerializer  # для переводов текста parler
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers
from rest_framework.serializers import SerializerMethodField

from catalog.models import Category, Dish, UOM
from delivery_contacts.models import Delivery, Restaurant
from promos.models import PromoNews, Promocode
from shop.models import (CartDish, Order, OrderDish,
                         ShoppingCart, ORDER_STATUS_CHOICES)
from tm_bot.models import MessengerAccount
from users.models import BaseProfile, UserAddress
from users.validators import (validate_birthdate,
                              validate_first_and_last_name)
from tm_bot.validators import (validate_msngr_username,
                               validate_messenger_account)
                                # validate_msngr_account,
                                # validate_msngr_type_username,
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from shop.validators import (validate_selected_month,
                             validate_delivery_time)
from django.utils.translation import get_language
from django.db import transaction
from shop.utils import get_base_profile_cartdishes_promocode, get_rep_dic
from delivery_contacts.utils import (
    google_validate_address_and_get_coordinates,
    combine_date_and_time)
from delivery_contacts.services import get_delivery_zone

User = get_user_model()


# ---------------- ЛИЧНЫЙ КАБИНЕТ --------------------
class MessengerAccountSerializer(serializers.ModelSerializer):
    msngr_username = serializers.CharField(
        validators=[validate_msngr_username,]
    )

    class Meta:
        model = MessengerAccount
        fields = ('msngr_username', 'msngr_type')
        read_only_fields = ('msngr_type',)


class MyUserSerializer(serializers.ModelSerializer):
    date_of_birth = serializers.DateField(
                        source='base_profile.date_of_birth',
                        required=False,
                        allow_null=True,
                        validators=[validate_birthdate,])

    messenger_account = MessengerAccountSerializer(
                        source='base_profile.messenger_account',
                        required=False,
                        allow_null=True,
                        validators=[validate_messenger_account,]
                        #  validate_msngr_account,])
    )
    first_name = serializers.CharField(
                        validators=[validate_first_and_last_name,])

    last_name = serializers.CharField(
                        validators=[validate_first_and_last_name,])

    phone = PhoneNumberField(required=True)

    class Meta:
        model = User
        fields = ('first_name', 'last_name',
                  'email', 'phone',
                  'date_of_birth',
                  'web_language',
                  'messenger_account',
                  )
        read_only_fields = ('email', 'date_of_birth')

    def update(self, instance: User, validated_data: dict) -> User:
        """
        Метод для редакции данных пользователя.
        Args:
            instance (User): изменяемый рецепт
            validated_data (dict): проверенные данные из запроса.
        Returns:
            User: созданный рецепт.
        """
        if 'base_profile' in validated_data:
            base_profile_validated_data = validated_data.pop('base_profile')

            if 'messenger_account' in base_profile_validated_data:
                messenger_account = base_profile_validated_data.get(
                    'messenger_account')
                if messenger_account is not None:
                    messenger_account = (
                        MessengerAccount.fulfill_messenger_account(
                            base_profile_validated_data.get(
                                'messenger_account')
                        )
                    )

                BaseProfile.base_profile_messegner_account_add(
                    messenger_account,
                    instance
                )

            if 'date_of_birth' in base_profile_validated_data:
                date_of_birth = base_profile_validated_data.get('date_of_birth')

                instance.base_profile.date_of_birth = date_of_birth

                instance.base_profile.save(
                    update_fields=['date_of_birth']
                )

        return super().update(instance, validated_data)


# --------       история заказов   ---------
class DishShortSerializer(TranslatableModelSerializer):
    """
    Сериализатор для минимального отображения инфо о Dish:
    картинка, описание - название и описание
    Возможно только чтение.
    """
    translations = TranslatedFieldsField(shared_model=Dish,
                                         read_only=True)

    class Meta:
        fields = ('article', 'id', 'translations', 'image')
        model = Dish

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        translations = rep['translations']
        # for lang, translation in translations["translations"].items():
        for lang, translation in translations.items():
            if "msngr_short_name" in translation:
                del translation["msngr_short_name"]
            if "msngr_text" in translation:
                del translation["msngr_text"]
        return rep


class OrderDishesShortSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для Orderdishes.
    Возможно только чтение.
    """
    dish = DishShortSerializer()

    class Meta:
        fields = ('dish', 'quantity', 'amount')
        model = OrderDish
        read_only_fields = ('dish', 'quantity', 'amount')


class UserOrdersSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для Orders.
    Возможно только чтение.
    """
    orderdishes = OrderDishesShortSerializer(many=True)
    status = serializers.CharField(source='get_status_display')

    class Meta:
        fields = ('id', 'order_number', 'created', 'status',
                  'orderdishes', 'final_amount_with_shipping')
        model = Order
        read_only_fields = ('id', 'order_number', 'created', 'status',
                            'orderdishes', 'final_amount_with_shipping')

    def get_orer_dishes(self, order: Order) -> QuerySet[dict]:
        """Получает список блюд заказа.

        Args:
            order (Order): Запрошенный заказ.

        Returns:
            QuerySet[dict]: Список блюд в заказе.
        """
        return order.orderdishes.values(
            'id',
            'translations',
            'amount'
        )


# --------       свои адреса   ---------


class UserAddressSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для сериализатора UserAddresses.
    Возможно создание, редактирование, удаление автором.
    """
    class Meta:
        fields = ('id', 'address')
        model = UserAddress

# --------       свои купоны   ---------
#
#
#


# ---------------- МЕНЮ: БЛЮДА и КАТЕГОРИИ --------------------

class UOMSerializer(TranslatableModelSerializer):
    """ Базовый сериализатор для ед-ц измерения."""
    translations = TranslatedFieldsField(shared_model=UOM,
                                         read_only=True)

    class Meta:
        fields = ('translations',)
        model = UOM
        read_only_fields = ('translations',)


class CategorySerializer(TranslatableModelSerializer):
    """ Базовый сериализатор для категории."""
    translations = TranslatedFieldsField(shared_model=Category,
                                         read_only=True)

    class Meta:
        fields = ('priority', 'translations', 'slug',)
        model = Category
        read_only_fields = ('priority', 'translations', 'slug',)


class DishMenuSerializer(TranslatableModelSerializer):
    """
    Сериализатор для краткого отображения блюд.
    """
    category = CategorySerializer(many=True,
                                  read_only=True)

    is_in_shopping_cart = SerializerMethodField(read_only=True)

    translations = TranslatedFieldsField(shared_model=Dish,
                                         read_only=True)

    weight_volume_uom = UOMSerializer(read_only=True)

    units_in_set_uom = UOMSerializer(read_only=True)

    class Meta:
        fields = ('article', 'priority',
                  'translations',
                  'category',
                  'price', 'final_price',
                  'spicy_icon', 'vegan_icon',
                  'image',
                  'weight_volume', 'weight_volume_uom',
                  'units_in_set', 'units_in_set_uom',
                  'is_in_shopping_cart',
                  )
        model = Dish
        read_only_fields = ('article', 'priority',
                            'translations',
                            'category',
                            'price', 'final_price',
                            'spicy_icon', 'vegan_icon',
                            'image',
                            'weight_volume', 'weight_volume_uom',
                            'units_in_set','units_in_set_uom',
                            'is_in_shopping_cart',
                            )

    def get_is_in_shopping_cart(self, dish: Dish) -> bool:
        """Получает булевое значение, если авторизованный пользователь имеет
        этот рецепт в корзине покупок.
        Args:
            dish (Dish): Запрошенное блюдо.
        Returns:
            bool: в корзине покупок или нет.
        """
        extra_kwargs = self.context.get('extra_kwargs', {})
        if extra_kwargs:
            cart_items = extra_kwargs.get('cart_items', None)
            if cart_items:
                return dish in cart_items
        return None

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        translations = rep['translations']
        for lang, translation in translations.items():
            if "msngr_short_name" in translation:
                del translation["msngr_short_name"]
            if "msngr_text" in translation:
                del translation["msngr_text"]
        return rep

# ---------------- РЕСТОРАНЫ + ДОСТАВКА + ПРОМО новости --------------------


class RestaurantSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для модели Restaurant, только чтение!
    """
    coordinates = serializers.SerializerMethodField()
    open_time = serializers.TimeField(format='%H:%M')
    close_time = serializers.TimeField(format='%H:%M')

    class Meta:
        fields = ('id', 'short_name',
                  'city', 'address', 'coordinates',
                  'open_time', 'close_time', 'phone',
                  'image')
        model = Restaurant
        read_only_fields = ('id', 'short_name',
                            'city', 'address', 'coordinates',
                            'open_time', 'close_time', 'phone',
                            'image')

    def get_coordinates(self, obj):
        # Извлекаем координаты из объекта модели и сериализуем их без SRID
        if obj.coordinates:
            return {
                'longitude': obj.coordinates.x,
                'latitude': obj.coordinates.y
            }
        else:
            return None

    def to_representation(self, instance):
        repr = super().to_representation(instance)
        repr['work_hours'] = f"{repr['open_time']} - {repr['close_time']}"
        return repr


class DeliverySerializer(TranslatableModelSerializer):
    """
    Базовый сериализатор для модели Delivery, только чтение!
    """
    translations = TranslatedFieldsField(shared_model=Delivery)

    class Meta:
        fields = ('id', 'city', 'type', 'translations', 'image')
        model = Delivery
        read_only_fields = ('id', 'city', 'type', 'translations', 'image')
        # добавить данные по мин стоимостям и пр


class ContatsDeliverySerializer(serializers.Serializer):
    """
    Базовый сериализатор для модели Delivery, только чтение!
    """
    restaurants = RestaurantSerializer(many=True)
    delivery = DeliverySerializer(many=True)


class PromoNewsSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для модели PromoNews, только чтение!
    """
    translations = TranslatedFieldsField(shared_model=PromoNews)

    class Meta:
        fields = ('id', 'city', 'translations', 'created',
                  'image_ru', 'image_en', 'image_sr_latn')
        model = PromoNews
        read_only_fields = ('id', 'city', 'translations', 'created',
                            'image_ru', 'image_en', 'image_sr_latn')


# --------------------------- КОРЗИНА ------------------------------


class DishCartDishSerializer(serializers.ModelSerializer):
    """
    Сериализатор для краткого отображения блюд.
    """
    translations = TranslatedFieldsField(shared_model=Dish,
                                         read_only=True)

    class Meta:
        fields = ('article', 'translations',
                  'image')
        model = Dish
        read_only_fields = ('article', 'translations',
                            'image')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        translations = instance.translations.all()
        translations_short_name = {}
        for translation in translations:
            if translation.short_name:
                translations_short_name[f'{translation.language_code}'] = translation.short_name
        rep['translations'] = translations_short_name
        return rep


class CartDishSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для модели CartDish.
    Все поля обязательны.
    """
    dish = DishCartDishSerializer(required=False, read_only=True)

    class Meta:
        fields = ('id', 'dish', 'quantity',
                  'unit_price', 'amount')
        model = CartDish
        read_only_fields = ('id', 'dish',
                            'unit_price', 'amount')


class ShoppingCartSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения модели ShoppingCart.
    """
    promocode = serializers.CharField(allow_null=True)
    cartdishes = CartDishSerializer(many=True,
                                    read_only=True)

    class Meta:
        fields = ('id', 'items_qty',
                  'amount', 'promocode',
                  'discounted_amount',
                  'cartdishes')
        model = ShoppingCart
        read_only_fields = ('id',
                            'amount',
                            'discounted_amount',
                            'cartdishes',
                            'items_qty')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.promocode:
            rep['promocode'] = instance.promocode.promocode
        return rep

    def validate_promocode(self, value):
        if value is not None:
            if not Promocode.is_valid(value):
                raise serializers.ValidationError(
                    {'promocode': ("Please check the promocode.")})
        return value

    def update(self, instance, validated_data):
        promocode = validated_data.get('promocode')
        if promocode is not None:
            instance.promocode = Promocode.objects.get(promocode=promocode)
        else:
            instance.promocode = None
        instance.save()
        return instance


# --------------------------- ЗАКАЗ ------------------------------

class OrderDishWriteSerializer(serializers.ModelSerializer):
    """
    Сериализатор для записи Orderdishes в заказ.
    """
    class Meta:
        fields = ('dish', 'quantity')
        model = OrderDish


class BaseOrderSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(required=False,
                                      allow_null=True,
                                      max_digits=8,
                                      decimal_places=2,
                                      write_only=True)
    promocode = serializers.CharField(required=False,
                                      allow_null=True,
                                      write_only=True)
    orderdishes = OrderDishWriteSerializer(required=False,
                                           allow_null=True,
                                           many=True)
    recipient_phone = PhoneNumberField(required=True)

    selected_month = serializers.DateField(format="%d.%B",
                                           required=True,
                                           allow_null=True,
                                           write_only=True,
                                           validators=[validate_selected_month,])

    selected_time = serializers.TimeField(format="%H:%M",
                                          required=True,
                                          allow_null=True,
                                          write_only=True)

    class Meta:
        fields = ('items_qty',
                  'recipient_name', 'recipient_phone',
                  'city', 'delivery_time', 'comment', 'persons_qty',
                  'orderdishes', 'amount', 'promocode')
        model = Order

    def validate(self, data):
        request = self.context.get('request')

        if request.user.is_authenticated:

            base_profile, cart, cartdishes, promocode = (
                get_base_profile_cartdishes_promocode(request.user)
            )
            data['base_profile'] = base_profile
            data['cart'] = cart
            data['cartdishes'] = cartdishes
            data['promocode'] = promocode



        delivery = self.context.get('extra_kwargs', {}).get('delivery')
        data['delivery'] = delivery

        delivery_time = combine_date_and_time(
            self.initial_data['selected_month'],
            self.initial_data['selected_time']
            )

        if delivery_time is not None:
            restaurant = data.get('restaurant', None)
            validate_delivery_time(delivery_time, delivery, restaurant)
        data['delivery_time'] = delivery_time

        return data


class TakeawayOrderSerializer(BaseOrderSerializer):
    restaurant = serializers.PrimaryKeyRelatedField(
        queryset=Restaurant.objects.all(),
        required=True
    )

    class Meta(BaseOrderSerializer.Meta):
        fields = BaseOrderSerializer.Meta.fields + ('restaurant',)


class TakeawayOrderWriteSerializer(TakeawayOrderSerializer):
    status_display = serializers.SerializerMethodField()

    class Meta:
        fields = ('order_number', 'created',
                  'status_display',
                  'discounted_amount',
                  'payment_type',
                  'items_qty',
                  'recipient_name', 'recipient_phone',
                  'city', 'delivery_time', 'restaurant',
                  'comment', 'persons_qty',
                  'orderdishes', 'amount', 'promocode',
                  )
        model = Order
        read_only_fields = ('order_number', 'created',
                            'status',
                            'final_amount_with_shipping',
                            )

    def get_status_display(self, obj):
        # Получаем разъяснение статуса заказа по его значению
        status_display = dict(ORDER_STATUS_CHOICES).get(obj.status)
        return status_display

    def create(self, validated_data):

        language = self.context.get('request').LANGUAGE_CODE
        request = self.context.get('request')

        if request.data:
            if request.user.is_authenticated:

                base_profile, cart, cartdishes, promocode = (
                    get_base_profile_cartdishes_promocode(request.user)
                )

                user = validated_data.pop('base_profile')
                cart = validated_data.pop('cart')
                cartdishes = validated_data.pop('cartdishes')

                # validated_data['delivery'] = get_object_or_404(
                #                             Delivery,
                #                             city=self.initial_data['city'],
                #                             type='takeaway')

                # validated_data['promocode'] = promocode

                with transaction.atomic():
                    order = Order.objects.create(**validated_data,
                                                 user=user,
                                                 language=language)

                    OrderDish.create_orderdishes_from_cartdishes(
                        order, cartdishes)
                    # проверить единство расчетов фронт и бэк
                    # validated_data['discount'] = cart.discount
                    # validated_data['discounted_amount'] = cart.discounted_amount
                    # validated_data['items_qty'] = cart.items_qty
                    # validated_data['amount'] = cart.amount
                    cart.empty_cart()

            else:
                # Если пользователь не аутентифицирован, получаем данные корзины из запроса
                if 'cartdishes' in validated_data:
                    cartdishes = validated_data.pop('cartdishes')
                    order = Order.objects.create(**validated_data,
                                                 user=None,
                                                 language=language)
                    OrderDish.create_orderdishes_from_cartdishes(
                        order, cartdishes, base_profile=None)
            return order

        # Если что-то пошло не так или не было найдено корзины, возвращаем None
        return None

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["total"] = {
            "title": "Total amount",
            "total_amount": instance.final_amount_with_shipping
        }

        return rep



class TakeawayConditionsSerializer(serializers.ModelSerializer):
    restaurants = SerializerMethodField()

    class Meta:
        fields = ('city', 'restaurants',
                  'discount')
        model = Order
        read_only_fields = ('city', 'restaurants',
                            'discount')

    def get_restaurants(self, delivery: Delivery) -> QuerySet[dict]:
        """Получает список ресторанов города.

        Args:
            delivery (Delivery): Запрошенный объект доставки.

        Returns:
            QuerySet[dict]: Список ресторанов в городе.
        """
        city = delivery['city']
        restaurants = Restaurant.objects.filter(
            city=city,
            is_active=True
        )

        return RestaurantSerializer(restaurants, many=True).data


class DeliveryOrderSerializer(BaseOrderSerializer):
    recipient_address = serializers.CharField(required=True)

    class Meta(BaseOrderSerializer.Meta):
        fields = BaseOrderSerializer.Meta.fields + ('recipient_address',)

    def validate_recipient_address(self, value):
        try:
            lat, lon, status = google_validate_address_and_get_coordinates(value)

        except Exception as e:
            lat, lon, status = None, None, None

        self.initial_data['lat'], self.initial_data['lon'] = lat, lon

        return value


class DeliveryOrderWriteSerializer(DeliveryOrderSerializer):
    status_display = serializers.SerializerMethodField()

    class Meta:
        fields = ('order_number', 'created',
                  'status_display',
                  'final_amount_with_shipping',
                  'discounted_amount',
                  'delivery_cost',
                  'payment_type',
                  'items_qty',
                  'recipient_name', 'recipient_phone',
                  'city', 'delivery_time',
                  'comment', 'persons_qty',
                  'orderdishes', 'amount', 'promocode',
                  'recipient_address'
                  )
        model = Order
        read_only_fields = ('order_number', 'created',
                            'status', 'delivery_cost',
                            'final_amount_with_shipping',
                            )

    def get_status_display(self, obj):
        # Получаем разъяснение статуса заказа по его значению
        status_display = dict(ORDER_STATUS_CHOICES).get(obj.status)
        return status_display

    def create(self, validated_data):

        language = self.context.get('request').LANGUAGE_CODE
        request = self.context.get('request')

        if request.data:
            if request.user.is_authenticated:

                user = validated_data.pop('base_profile')
                cart = validated_data.pop('cart')
                cartdishes = validated_data.pop('cartdishes')

                validated_data['delivery_address_data'] = {
                    "lat": self.initial_data.get('lat'),
                    "lon": self.initial_data.get('lon')
                }
                validated_data['delivery_zone'] = get_delivery_zone(
                    self.validated_data.get('city'),
                    self.initial_data.get('lat'),
                    self.initial_data.get('lon')
                )

                with transaction.atomic():
                    order = Order.objects.create(**validated_data,
                                                 user=user,
                                                 language=language)

                    OrderDish.create_orderdishes_from_cartdishes(
                        order, cartdishes)
                    # проверить единство расчетов фронт и бэк
                    # validated_data['discount'] = cart.discount
                    # validated_data['discounted_amount'] = cart.discounted_amount
                    # validated_data['items_qty'] = cart.items_qty
                    # validated_data['amount'] = cart.amount
                    cart.empty_cart()

            else:
                # Если пользователь не аутентифицирован, получаем данные корзины из запроса
                if 'cartdishes' in validated_data:
                    cartdishes = validated_data.pop('cartdishes')
                    order = Order.objects.create(**validated_data,
                                                 user=None,
                                                 language=language)
                    OrderDish.create_orderdishes_from_cartdishes(
                        order, cartdishes, base_profile=None)
            return order

        # Если что-то пошло не так или не было найдено корзины, возвращаем None
        return None

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep = get_rep_dic(rep, instance=instance)

        del rep["final_amount_with_shipping"]
        del rep["delivery_cost"]

        return rep


class DeliveryConditionsSerializer(serializers.ModelSerializer):

    class Meta:
        fields = ('city', 'min_order_amount',
                  'min_time', 'max_time',
                  'default_delivery_cost',
                  'discount')
        model = Delivery
        read_only_fields = ('city', 'min_order_amount',
                            'min_time', 'max_time',
                            'default_delivery_cost',
                            'discount')














#############------------------------------------------------------------------------------------------------------------------------#####

# from django.contrib.auth import get_user_model
# from django.db.models import F, QuerySet
# from drf_extra_fields.fields import Base64ImageField
# from rest_framework import serializers
# from rest_framework.serializers import SerializerMethodField

# from foodgram.settings import DEFAULT_RECIPES_LIMIT
# from recipe.models import Favorit, Ingredient, Recipe, ShoppingCartUser, Tag
# from user.models import Subscription

# User = get_user_model()


# class UserSerializer(serializers.ModelSerializer):
#     """
#     Базовый сериализатор для модели User.
#     Все поля обязательны
#     Валидация:
#     1) проверка, что переданный username не 'me';
#     2) проверка уникальности полей email и username по БД.
#     """
#     is_subscribed = serializers.SerializerMethodField()

#     class Meta:
#         fields = ('id', 'username', 'email', 'first_name',
#                   'last_name', 'is_subscribed',
#                   )
#         model = User

#     def validate_username(self, value: str) -> str:
#         if value.lower() == 'me':
#             raise serializers.ValidationError(
#                 "Использовать 'me' в качестве username запрещено."
#             )
#         return value

#     def get_is_subscribed(self, obj) -> bool:
#         """Проверка подписки пользователей.

#         Определяет - подписан ли текущий пользователь
#         на просматриваемого пользователя.

#         Args:
#             obj (User): Пользователь, на которого проверяется подписка.

#         Returns:
#             bool: True, если подписка есть. Во всех остальных случаях False.
#         """
#         request = self.context['request']
#         return Subscription.objects.filter(
#             user=request.user.id,
#             author=obj.id
#         ).exists()


# class SignUpSerializer(UserSerializer):
#     """
#     Сериализатор для регистрации нового пользователя.
#     Все поля обязательны.
#     Валидация:
#      - Если в БД есть пользователи с переданными email или username,
#     вызывается ошибка.
#      - Если имя пользователя - me, вызывается ошибка.
#     """
#     email = serializers.EmailField(
#         max_length=254,
#         required=True
#     )
#     username = serializers.RegexField(
#         regex=r'^[\w.@+-]+$',
#         max_length=150,
#         min_length=8
#     )
#     password = serializers.CharField(
#         write_only=True,
#         required=True,
#         max_length=150,
#         min_length=8
#     )

#     class Meta:
#         fields = ('id', 'username', 'email', 'first_name',
#                   'last_name', 'password')
#         read_only_fields = ('id',)
#         model = User

#     def validate(self, data: dict) -> dict:
#         username = data['username']
#         email = data['email']
#         password = data['password']
#         if User.objects.filter(username=username).exists():
#             raise serializers.ValidationError(
#                 "Пользователь с таким username уже существует."
#             )
#         if User.objects.filter(email=email).exists():
#             raise serializers.ValidationError(
#                 "Пользователь с таким email уже существует."
#             )
#         if password is None:
#             raise serializers.ValidationError(
#                 "Придумайте пароль."
#             )
#         return data

#     def create(self, validated_data: dict) -> User:
#         """ Создаёт нового пользователя с запрошенными полями.
#         Args:
#             validated_data (dict): Полученные проверенные данные.
#         Returns:
#             User: Созданный пользователь.
#         """
#         user = User(
#             email=validated_data['email'],
#             username=validated_data['username'],
#             first_name=validated_data['first_name'],
#             last_name=validated_data['last_name'],
#         )
#         user.set_password(validated_data['password'])
#         user.save()
#         return user


# class PasswordSerializer(serializers.Serializer):
#     """
#     Сериалайзер для данных, получаемых для смены пароля
#     актуального пользователя.
#     """
#     new_password = serializers.CharField(write_only=True)
#     current_password = serializers.CharField(write_only=True)

#     def validate_current_password(self, value: str) -> str:
#         user = self.initial_data['user']
#         if not user.check_password(value):
#             raise serializers.ValidationError(
#                 'Введен неверный текущий пароль.'
#             )
#         return value

#     def validate_new_password(self, value: str) -> str:
#         if value == self.initial_data['current_password']:
#             raise serializers.ValidationError(
#                 'Новый пароль должен отличаться от старого!'
#             )
#         return value


# class RecipesShortSerializer(serializers.ModelSerializer):
#     """
#     Сериализатор для краткого отображения рецептов.
#     """
#     image = Base64ImageField()

#     class Meta:
#         fields = ('id', 'image', 'cooking_time', 'name')
#         model = Recipe
#         read_only_fields = ('id', 'image', 'cooking_time', 'name')


# class SubscriptionsSerializer(UserSerializer):
#     """
#     Сериализатор для отображения данных о рецептах и их авторов, находящихся
#     в подписках у актуального пользователя.
#     """
#     recipes = serializers.SerializerMethodField()
#     is_subscribed = serializers.SerializerMethodField()
#     recipes_count = serializers.SerializerMethodField()

#     class Meta:
#         fields = ('id', 'username', 'email', 'first_name',
#                   'last_name', 'is_subscribed', 'recipes',
#                   'recipes_count',
#                   )
#         model = User

#     def get_recipes(self, obj: User) -> dict:
#         """ Получает список рецептов автора, на которого оформлена подписка
#         и возвращает кол-во, переданное в параметр запроса recipes_limit,
#         переданного в URL.
#         Args:
#             user (User): Автор на которого подписан пользователь.
#         Returns:
#             QuerySet: список рецептов автора из подписки.
#         """
#         recipes_limit = self.context['recipes_limit']
#         if recipes_limit is None:
#             recipes_limit = DEFAULT_RECIPES_LIMIT
#         else:
#             recipes_limit = int(recipes_limit)
#         serializer = RecipesShortSerializer(
#             obj.recipes.all()[:recipes_limit],
#             many=True
#         )
#         return serializer.data

#     def get_recipes_count(self, obj: User) -> int:
#         """Получает количество рецептов всех подписанных авторов.
#         Args:
#             obj (User): автор, на которого подписан пользователь.
#         Returns:
#             int: Колличество рецептов автора из подписки пользователя.
#         """
#         return obj.recipes_count


# class TagSerializer(serializers.ModelSerializer):
#     """ Базовый сериализатор тэгов."""
#     class Meta:
#         fields = ('id', 'name', 'color', 'slug')
#         model = Tag
#         read_only_fields = ('id', 'name', 'color', 'slug')


# class IngredientSerializer(serializers.ModelSerializer):
#     """ Базовый сериализатор ингредиентов."""
#     class Meta:
#         fields = ('id', 'name', 'measurement_unit')
#         model = Ingredient


# class RecipeReadSerializer(serializers.ModelSerializer):
#     """
#     Сериализатор для полного отображения рецептов.
#     Только для чтения.
#     """
#     tags = TagSerializer(many=True)
#     ingredients = SerializerMethodField()
#     author = UserSerializer()
#     image = Base64ImageField()
#     is_favorited = SerializerMethodField()
#     is_in_shopping_cart = SerializerMethodField()

#     class Meta:
#         fields = ('id', 'tags', 'author',
#                   'name', 'image', 'text', 'cooking_time',
#                   'ingredients', 'is_favorited', 'is_in_shopping_cart'
#                   )
#         model = Recipe
#         read_only_fields = ('id', 'author', 'tags'
#                             'name', 'image', 'text', 'cooking_time',
#                             'ingredients')

#     def get_ingredients(self, recipe: Recipe) -> QuerySet[dict]:
#         """Получает список ингридиентов для рецепта.

#         Args:
#             recipe (Recipe): Запрошенный рецепт.

#         Returns:
#             QuerySet[dict]: Список ингридиентов в рецепте.
#         """
#         return recipe.ingredients.values(
#             'id',
#             'name',
#             'measurement_unit',
#             amount=F('recipe__amount')
#         )

#     def get_is_favorited(self, recipe: Recipe) -> bool:
#         """Получает булевое значение, если авторизованный пользователь имеет
#         этот рецепт в избранном.
#         Args:
#             recipe (Recipe): Запрошенный рецепт.
#         Returns:
#             bool: в избранных или нет.
#         """
#         request = self.context['request']
#         return Favorit.objects.filter(
#             favoriter=request.user.id,
#             recipe=recipe.id
#         ).exists()

#     def get_is_in_shopping_cart(self, recipe: Recipe) -> bool:
#         """Получает булевое значение, если авторизованный пользователь имеет
#         этот рецепт в корзине покупок.
#         Args:
#             recipe (Recipe): Запрошенный рецепт.
#         Returns:
#             bool: в корзине покупок или нет.
#         """
#         request = self.context['request']
#         return ShoppingCartUser.objects.filter(
#             owner=request.user.id,
#             recipe=recipe.id
#         ).exists()


# class IngredientAmountSerializer(serializers.Serializer):
#     """
#     Сериализатор для записи ингредиентов и их колличества в рецепт.
#     Валидация проверяет, что колличество ингредиента > 0.
#     Так же автоматически прверяется наличие полей id, amount.
#     """
#     id = serializers.PrimaryKeyRelatedField(
#         queryset=Ingredient.objects.all()
#     )
#     amount = serializers.IntegerField()

#     def validate_amount(self, value: int) -> int:
#         if value <= 0:
#             raise serializers.ValidationError(
#                 "Колличество ингредиента должно быть больше 0."
#             )
#         return value


# class RecipeSerializer(serializers.ModelSerializer):
#     """
#     Сериализатор для записи рецептов.
#     Валидация полей ingredients, tags на наличией хотя бы 1 записи.
#     Описаны методы сохранения и изменения рецепта.
#     Для представления сохраненного/измененного рецепта используется
#     RecipeReadSerializer.
#     """
#     tags = serializers.PrimaryKeyRelatedField(
#         many=True, queryset=Tag.objects.all()
#     )
#     ingredients = IngredientAmountSerializer(many=True, required=True)
#     author = UserSerializer(read_only=True)
#     image = Base64ImageField()

#     class Meta:
#         fields = ('author', 'name', 'image', 'text', 'cooking_time',
#                   'ingredients', 'tags')
#         model = Recipe

#     def validate(self, data: dict) -> dict:
#         """
#         Проверка данных, введенных в полях ingredients, tags.
#         Обработка изображения для сохранения в БД.
#         Проверка колличества проведена в сериализаторе
#         IngredientAmountSerializer.
#         Args:
#             data (dict): непроверенные данные из запроса.
#         Returns:
#             dict: данные, прошедшие проверку.
#         """
#         ingredients = data.get('ingredients')
#         tags = data.get('tags')
#         if len(ingredients) == 0:
#             raise serializers.ValidationError({
#                 'ingredients':
#                     'Выберите хотя бы 1 ингредиент.'
#             })
#         ingr_list = []
#         for ingredient in ingredients:
#             if ingredient['id'] in ingr_list:
#                 raise serializers.ValidationError({
#                     "ingredients": [
#                         {
#                             "id": [
#                                 "Проверьте ингредиенты на повторение."
#                             ]
#                         },
#                     ]
#                 })
#             ingr_list.append(ingredient['id'])

#         if len(tags) == 0:
#             raise serializers.ValidationError({
#                 'tags': 'Выберите хотя бы 1 тэг.'
#             })
#         return data

#     def create(self, validated_data: dict) -> Recipe:
#         """
#         Метод для создания рецепта.
#         Args:
#             validated_data (dict): проверенные данные из запроса.
#         Returns:
#             Recipe: созданный рецепт.
#         """
#         ingredients = validated_data.pop('ingredients')
#         tags = validated_data.pop('tags')
#         request = self.context['request']
#         recipe = Recipe.objects.create(**validated_data, author=request.user)
#         recipe.load_ingredients(ingredients)
#         recipe.tags.set(tags)
#         return recipe

#     def update(self, instance: Recipe, validated_data: dict) -> Recipe:
#         """
#         Метод для редакции рецепта.
#         Args:
#             instance (Recipe): изменяемый рецепт
#             validated_data (dict): проверенные данные из запроса.
#         Returns:
#             Recipe: созданный рецепт.
#         """
#         ingredients = validated_data.pop('ingredients')
#         tags = validated_data.pop('tags')
#         super().update(instance, validated_data)
#         instance.ingredients.clear()
#         instance.load_ingredients(ingredients)
#         instance.tags.clear()
#         instance.tags.set(tags)
#         return instance

#     def to_representation(self, instance: Recipe) -> dict:
#         """
#         Метод для выбора RecipeReadSerializer сериализатором для
#         отображения созданного/измененного рецепта.
#         """
#         serializer = RecipeReadSerializer(instance)
#         serializer.context['request'] = self.context['request']
#         return serializer.data

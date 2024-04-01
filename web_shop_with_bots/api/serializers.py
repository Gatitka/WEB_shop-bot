
from typing import Dict
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from parler_rest.fields import TranslatedFieldsField
from parler_rest.serializers import TranslatableModelSerializer
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers
from rest_framework.serializers import SerializerMethodField
from catalog.models import UOM, Category, Dish
from catalog.validators import get_dish_validate_exists_active
from delivery_contacts.models import Delivery, Restaurant
from delivery_contacts.services import get_delivery_zone
from delivery_contacts.utils import google_validate_address_and_get_coordinates
from promos.models import PrivatPromocode, Promocode, PromoNews
from promos.services import get_promocode_discount_amount
from shop.models import (ORDER_STATUS_CHOICES, CartDish, Order, OrderDish,
                         ShoppingCart)
from shop.services import get_amount
from shop.validators import validate_delivery_time
from tm_bot.models import MessengerAccount
from tm_bot.validators import (validate_messenger_account,
                               validate_msngr_username)
from users.models import BaseProfile, UserAddress
from users.validators import validate_birthdate, validate_first_and_last_name
from promos.validators import get_promocode_validate_active_in_timespan
from .services import get_rep_dic
# from shop.services import get_base_profile_cartdishes_promocode
# from promos.validators import validator_promocode
# from django.utils.translation import get_language
# from django.core.validators import EmailValidator
# from django.conf import settings

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
                  'messenger_account', 'is_subscribed'
                  )
        read_only_fields = ('email', 'date_of_birth')

    # def validate(self, attrs):
    #     req = self.context['request']
    #     language_code=req.LANGUAGE_CODE
    #     print(language_code)

    def update(self, instance: User,
               validated_data: Dict[str, any]) -> User:
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
                date_of_birth = (
                    base_profile_validated_data.get('date_of_birth')
                )

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

    def to_representation(self, instance):
        if instance is None:
            return {'detail': 'Адрес не доступен.'}
            # Возвращаем сообщение об ошибке
        return super().to_representation(instance)

# --------       свои купоны   ---------


class UserPromocodeSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для UserPromocodes.
    Возможно только чтение.
    """
    class Meta:
        fields = ('id', 'promocode',
                  'valid_from', 'valid_to')
        model = PrivatPromocode


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
                            'units_in_set', 'units_in_set_uom',
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
    workhours = serializers.SerializerMethodField()

    class Meta:
        fields = ('id',
                  'address', 'coordinates',
                  'open_time', 'close_time', 'phone',
                  'workhours')
        model = Restaurant
        geo_field = 'coordinates'
        read_only_fields = ('id',
                            'address', 'coordinates',
                            'open_time', 'close_time', 'phone',
                            'workhours')

    def get_coordinates(self, obj):
        # Извлекаем координаты из объекта модели и сериализуем их без SRID
        if obj.coordinates:
            return {
                'longitude': obj.coordinates.x,
                'latitude': obj.coordinates.y
            }
        else:
            return None

    def get_workhours(self, obj):
        # Извлекаем координаты из объекта модели и сериализуем их без SRID
        min_time = obj.open_time
        max_time = obj.close_time

        min_time_str = min_time.strftime('%H:%M')
        max_time_str = max_time.strftime('%H:%M')

        return f"{min_time_str} - {max_time_str}"


class DeliverySerializer(TranslatableModelSerializer):
    """
    Базовый сериализатор для модели Delivery, только чтение!
    """
    translations = TranslatedFieldsField(shared_model=Delivery)

    class Meta:
        fields = ('id', 'type', 'translations', 'image')
        model = Delivery
        read_only_fields = ('id', 'city', 'type', 'translations', 'image')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if rep.get('type') == 'takeaway':
            del rep['image']

        return rep


class ContactsDeliverySerializer(serializers.Serializer):
    """
    Базовый сериализатор для модели Delivery, только чтение!
    """
    city = serializers.CharField()
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


class DishShortLocaleSerializer(serializers.ModelSerializer):
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
                translations_short_name[
                    f'{translation.language_code}'] = translation.short_name
        rep['translations'] = translations_short_name
        return rep


class DishField(serializers.RelatedField):
    def to_representation(self, value):
        return value

    def to_internal_value(self, data):
        if data is not None:
            dish = get_dish_validate_exists_active(data)
            return dish
        return data


class CartDishSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для модели CartDish.
    """
    dish = DishField(queryset=Dish.objects.filter(is_active=True),
                     required=True)

    class Meta:
        fields = ('id', 'dish', 'quantity',)
        model = CartDish
        read_only_fields = ('id',)
        #                     'dish', 'unit_price', 'amount')


class PromoCodeField(serializers.RelatedField):
    def to_representation(self, value):
        return {"promocode": f"{value.code}",
                "status": "valid"}

    def to_internal_value(self, data):
        if data is not None:
            promocode = get_promocode_validate_active_in_timespan(data)
            return promocode

        return data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения модели ShoppingCart.
    """
    amount = serializers.DecimalField(required=False,
                                      allow_null=True,
                                      max_digits=8,
                                      decimal_places=2,
                                      )
    # promocode = PromoCodeField(
    #     queryset=Promocode.objects.filter(is_active=True),
    #     required=False, allow_null=True,
    #     )
    cartdishes = CartDishSerializer(required=False,
                                    allow_null=True,
                                    many=True,
                                    )

    class Meta:
        fields = ('cartdishes',
                  'amount')
                  # 'id', 'items_qty',
                  # , 'promocode', 'discount',
                  # 'discounted_amount',
                  # , 'message')
        model = ShoppingCart
        # read_only_fields = ('id',
        #                     'discount',
        #                     'discounted_amount',
        #                     'items_qty', 'message')

    # def validate_promocode(self, value):
    #     if value is None:
    #         return value

    #     value.is_valid()
    #     if value.first_order:
    #         user = self.context['request'].user
    #         if user.is_authenticated:
    #             orders_count = user.base_profile.orders.count()
    #             if orders_count > 0:
    #                 raise serializers.ValidationError({
    #                     "message": _("This promo code is applicable only for "
    #                                  "the first order."),
    #                     "status": "invalid"})
    #         # else:
    #         #     raise serializers.ValidationError({
    #         #         "message": ("This promo code is applicable only for "
    #         #                     "the first order. "
    #         #                     "Will be applied after order "
    #         #                     "form filling in."),
    #         #         "status": "valid"})
    #     return value

    # def update(self, instance, validated_data):
    #     promocode = validated_data.get('promocode')
    #     if promocode is not None:
    #         instance.promocode = promocode
    #     else:
    #         instance.promocode = None
    #     instance.save()
    #     return instance

    # def get_message(self, instance):
    #     disc_am, message, free_delivery = (
    #         get_promocode_discount_amount(instance.promocode,
    #                                       amount=instance.amount)
    #     )
    #     return message

# --------------------------- ЗАКАЗ ------------------------------


class OrderDishWriteSerializer(serializers.ModelSerializer):
    """
    Сериализатор для записи Orderdishes в заказ.
    """

    dish = DishField(queryset=Dish.objects.filter(is_active=True),
                     required=True)

    class Meta:
        fields = ('dish', 'quantity')
        model = OrderDish


class BaseOrderSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(required=False,
                                      allow_null=True,
                                      max_digits=8,
                                      decimal_places=2,
                                      write_only=True)
    promocode = PromoCodeField(
        queryset=Promocode.objects.filter(is_active=True),
        required=False, allow_null=True)

    orderdishes = OrderDishWriteSerializer(required=True,
                                           allow_null=False,
                                           many=True,
                                           )
    recipient_phone = PhoneNumberField(required=True)

    delivery_time = serializers.DateTimeField(format="%d.%B.%Y %H:%M",
                                              required=False,
                                              allow_null=True)

    city = serializers.CharField(max_length=20, required=True)

    recipient_phone = PhoneNumberField(write_only=True)

    class Meta:
        fields = ('recipient_phone',
                  'city', 'delivery_time',
                  'orderdishes', 'amount', 'promocode')
        model = Order

    def validate_city(self, value):
        valid_cities = [city[0] for city in settings.CITY_CHOICES]
        if value not in valid_cities:
            raise serializers.ValidationError(
                _("City is incorect."))
        return value

    def validate_delivery_time(self, value):
        delivery = self.context.get('extra_kwargs', {}).get('delivery')
        self.delivery = delivery

        if value is not None:
            restaurant = self.initial_data.get('restaurant', None)
            validate_delivery_time(value, delivery, restaurant)
        return value

    def validate_promocode(self, value):
        if value is None:
            return value

        if value.free_delivery:
            delivery = self.delivery
            if delivery.type != 'delivery':
                raise serializers.ValidationError(
                        _("This promocode is applicable only "
                          "for delivery orders."))

        if value.first_order:
            user = self.context['request'].user
            if user.is_authenticated:
                if user.base_profile.orders.exists():
                    raise serializers.ValidationError(
                        _("This promocode is applicable only "
                          "for the first order."))
            else:
                phone = self.initial_data.get('recipient_phone')
                if Order.objects.filter(recipient_phone=phone).exists():
                    raise serializers.ValidationError(
                        _("This promocode is applicable only "
                          "for the first order."))

        return value

    # в validate методе может быть просчет и сохранение amount.
    # валидация промокода на мин сумму, заказа на мин сумму.
    def validate(self, data):

        if data.get('promocode') and data['promocode'].min_order_amount:
            amount = get_amount(items=data.get('orderdishes'))
            if amount < data['promocode'].min_order_amount:
                raise serializers.ValidationError(
                        _("This promocode requires order amount ."))

        # if request.user.is_authenticated:

        #     base_profile, cart, cartdishes, promocode = (
        #         get_base_profile_cartdishes_promocode(request.user)
        #     )
        #     data['base_profile'] = base_profile
        #     data['cart'] = cart
        #     data['cartdishes'] = cartdishes
        #     data['promocode'] = promocode

        return data


class TakeawayOrderSerializer(BaseOrderSerializer):
    restaurant = serializers.PrimaryKeyRelatedField(
        queryset=Restaurant.objects.filter(is_active=True),
        required=True
    )

    class Meta(BaseOrderSerializer.Meta):
        fields = BaseOrderSerializer.Meta.fields + (
                    'restaurant', 'items_qty',
                    'recipient_name', 'comment', 'persons_qty')


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
                            'status'
                            )

    def get_status_display(self, obj):
        # Получаем разъяснение статуса заказа по его значению
        status_display = dict(ORDER_STATUS_CHOICES).get(obj.status)
        return status_display

    def create(self, validated_data):

        language = self.context.get('request').LANGUAGE_CODE
        request = self.context.get('request')

        if request.user.is_authenticated:
            user = validated_data.pop('base_profile')
        else:
            user = None

        if 'orderdishes' in validated_data:
            orderdishes = validated_data.pop('orderdishes')

            with transaction.atomic():
                order = Order.objects.create(**validated_data,
                                             user=user,
                                             language=language)

                OrderDish.create_orderdishes_from_cartdishes(
                    order, no_cart_cartdishes=orderdishes)

            # cart = validated_data.pop('cart')
            # cartdishes = validated_data.pop('cartdishes')

            # with transaction.atomic():
            #     order = Order.objects.create(**validated_data,
            #                                  user=user,
            #                                  language=language)

            #     OrderDish.create_orderdishes_from_cartdishes(
            #         order, cartdishes=cartdishes)

                # проверить единство расчетов фронт и бэк

        # else:
        #     # Если пользователь не аутентифицирован, получаем данные
        #     # orderdishes из сериализатора
        #     if 'orderdishes' in validated_data:
        #         orderdishes = validated_data.pop('orderdishes')

        #         with transaction.atomic():
        #             order = Order.objects.create(**validated_data,
        #                                          user=user,
        #                                          language=language)

        #             OrderDish.create_orderdishes_from_cartdishes(
        #                 order, no_cart_cartdishes=orderdishes)

                    # проверить единство расчетов фронт и бэк

        return order

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
        fields = BaseOrderSerializer.Meta.fields + (
                    'recipient_address', 'items_qty',
                    'recipient_name', 'comment', 'persons_qty')

    def validate_recipient_address(self, value):
        try:
            lat, lon, status = (
                google_validate_address_and_get_coordinates(value)
            )

        except Exception as e:
            lat, lon, status = None, None, None

        self.initial_data['lat'], self.initial_data['lon'] = lat, lon
        self.initial_data['delivery_address_data'] = {
                "lat": lat,
                "lon": lon
        }

        return value


class DeliveryOrderWriteSerializer(DeliveryOrderSerializer):
    status_display = serializers.SerializerMethodField()

    class Meta:
        fields = ('order_number', 'created',
                  'status_display',
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
                            )

    def get_status_display(self, obj):
        # Получаем разъяснение статуса заказа по его значению
        status_display = dict(ORDER_STATUS_CHOICES).get(obj.status)
        return status_display

    def create(self, validated_data):

        language = self.context.get('request').LANGUAGE_CODE
        request = self.context.get('request')

        validated_data['delivery_zone'] = get_delivery_zone(
                self.validated_data.get('city'),
                self.initial_data.get('lat'),
                self.initial_data.get('lon')
            )

        if request.user.is_authenticated:
            user = validated_data.pop('base_profile')
        else:
            user = None

        if 'orderdishes' in validated_data:
            orderdishes = validated_data.pop('orderdishes')

            with transaction.atomic():
                order = Order.objects.create(**validated_data,
                                             user=user,
                                             language=language)

                OrderDish.create_orderdishes_from_cartdishes(
                    order, no_cart_cartdishes=orderdishes)
            # cart = validated_data.pop('cart')
            # cartdishes = validated_data.pop('cartdishes')

            # validated_data['delivery_address_data'] = {
            #     "lat": self.initial_data.get('lat'),
            #     "lon": self.initial_data.get('lon')
            # }

            # with transaction.atomic():
            #     order = Order.objects.create(**validated_data,
            #                                  user=user,
            #                                  language=language)

            #     OrderDish.create_orderdishes_from_cartdishes(
            #         order, cartdishes)

                # проверить единство расчетов фронт и бэк

        # else:
        #     # Если пользователь не аутентифицирован, получаем данные
        #     # orderdishes из сериализатора
        #     if 'orderdishes' in validated_data:
        #         orderdishes = validated_data.pop('orderdishes')

        #         with transaction.atomic():
        #             order = Order.objects.create(**validated_data,
        #                                          user=None,
        #                                          language=language)

        #             OrderDish.create_orderdishes_from_cartdishes(
        #                 order, no_cart_cartdishes=orderdishes)

                    # проверить единство расчетов фронт и бэк
        return order

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep = get_rep_dic(rep, instance=instance)

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

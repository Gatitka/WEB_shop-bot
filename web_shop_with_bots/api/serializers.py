
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
from delivery_contacts.utils import (
    google_validate_address_and_get_coordinates,
    parce_coordinates)
from promos.models import PrivatPromocode, Promocode, PromoNews
from shop.models import (CartDish, Order, OrderDish,
                         ShoppingCart, get_amount)
from shop.validators import (validate_delivery_time, validate_payment_type,
                             validate_city)
from shop.utils import split_and_get_comment
from tm_bot.models import MessengerAccount
from tm_bot.validators import (validate_messenger_account,
                               validate_msngr_username)
from users.models import BaseProfile, UserAddress, validate_phone_unique
from users.validators import (validate_birthdate,
                              validate_first_and_last_name,
                              coordinates_validator, validate_language)
from promos.validators import get_promocode_validate_active_in_timespan
from .services import get_rep_dic
from decimal import Decimal
from tm_bot.services import send_message_new_order
from djoser.serializers import UserCreateSerializer
# from shop.services import get_base_profile_cartdishes_promocode
# from promos.validators import validator_promocode
# from django.utils.translation import get_language
# from django.core.validators import EmailValidator
# from django.conf import settings
from django.utils.translation import get_language

import logging
logger = logging.getLogger(__name__)


User = get_user_model()
# 'users.WEBAccount'


# ---------------- ЛИЧНЫЙ КАБИНЕТ --------------------
class MessengerAccountSerializer(serializers.ModelSerializer):
    msngr_username = serializers.CharField(
        validators=[validate_msngr_username,]
    )

    class Meta:
        model = MessengerAccount
        fields = ('msngr_username', 'msngr_type')
        read_only_fields = ('msngr_type',)


class LanguageField(serializers.CharField):

    def to_internal_value(self, data):
        if data is not None:
            valid_languages = [language[0] for language in settings.LANGUAGES]
            if data in valid_languages:
                return data
        return settings.DEFAULT_CREATE_LANGUAGE

    def to_representation(self, value):
        return value


class MyUserCreateSerializer(UserCreateSerializer):
    # web_language = LanguageField(required=False, allow_null=True, write_only=True)

    def validate(self, attrs):
        # Вызываем метод validate родительского класса и передаем в него атрибуты attrs
        attrs = super().validate(attrs)
        # Получаем запрос из контекста
        request = self.context.get('request')
        if request:
            # Получаем язык из запроса
            language = get_language()

            # Проводим валидацию языка
            if language:
                attrs['web_language'] = validate_language(language)
        # Возвращаем валидированные атрибуты
        return attrs


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

    phone = PhoneNumberField(required=True) # ,
                             #validators=[validate_phone_unique,])

    class Meta:
        model = User
        fields = ('first_name', 'last_name',
                  'email', 'phone',
                  'date_of_birth',
                  'messenger_account', 'is_subscribed',
                  )
        read_only_fields = ('email', 'date_of_birth')

    def validate(self, attrs):
        request = self.context['request']
        phone = self.initial_data['phone']
        validate_phone_unique(phone, request.user)
        return super().validate(attrs)

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


# # --------       история заказов   ---------

class DishShortSerializer(serializers.ModelSerializer):
    """
    Сериализатор для краткого отображения блюд.
    """
    translations = TranslatedFieldsField(shared_model=Dish,
                                         read_only=True)

    class Meta:
        fields = ('article', 'translations')
        model = Dish
        read_only_fields = ('article', 'translations')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        translations = rep['translations']
        for lang, translation in translations.items():
            if "msngr_short_name" in translation:
                del translation["msngr_short_name"]
            if "msngr_text" in translation:
                del translation["msngr_text"]
        return rep

    def to_internal_value(self, data):
        if data is not None:
            dish = get_dish_validate_exists_active(data)
            return dish
        return data


class DishWithImageSerializer(DishShortSerializer):
    """
    Сериализатор для блюд с изображением.
    """

    class Meta:
        fields = DishShortSerializer.Meta.fields + ('image',)
        model = Dish


class OrderDishesShortSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для Orderdishes.
    Возможно только чтение.
    """
    dish = DishWithImageSerializer()

    class Meta:
        fields = ('dish', 'quantity', 'unit_amount')
        model = OrderDish
        read_only_fields = ('dish', 'quantity', 'unit_amount')


class UserOrdersSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для Orders.
    Возможно только чтение.
    """
    orderdishes = OrderDishesShortSerializer(many=True)
    status = serializers.SerializerMethodField()

    class Meta:
        fields = ('id', 'order_number', 'created', 'status',
                  'orderdishes', 'final_amount_with_shipping')
        model = Order
        read_only_fields = ('id', 'order_number', 'created', 'status',
                            'orderdishes', 'final_amount_with_shipping')

    def get_status(self, obj):
        # Получаем разъяснение статуса заказа по его значению
        statuses_transl = settings.ORDER_STATUS_TRANSLATIONS
        status_transl = statuses_transl[obj.status]
        return status_transl

    def get_order_dishes(self, order: Order) -> QuerySet[dict]:
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


class DishArtIdSerializer(TranslatableModelSerializer):
    """
    Сериализатор для минимального отображения инфо о Dish:
    картинка, описание - название и описание
    Возможно только чтение.
    """

    class Meta:
        fields = ('article', 'id')
        model = Dish


class RepeatOrderDishesSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для Orderdishes.
    Возможно только чтение.
    """
    dish = DishArtIdSerializer()

    class Meta:
        fields = ('dish', 'quantity')
        model = OrderDish
        read_only_fields = ('dish', 'quantity')


class RepeatOrderSerializer(serializers.ModelSerializer):
    """
    Сериализатор для повторения заказа
    """
    orderdishes = RepeatOrderDishesSerializer(many=True, read_only=True)
    delivery_type = serializers.SerializerMethodField(read_only=True)

    class Meta:
        fields = ('orderdishes', 'recipient_name', 'recipient_phone',
                  'comment', 'city', 'persons_qty', 'my_delivery_address',
                  'delivery_type', 'recipient_address', 'restaurant',
                  'coordinates', 'address_comment')
        model = Order
        read_only_fields = ('orderdishes',
                            'recipient_name', 'recipient_phone',
                            'comment', 'city', 'persons_qty',
                            'delivery_type', 'restaurant',
                            'recipient_address', 'my_delivery_address',
                            'coordinates', 'address_comment')

    def get_delivery_type(self, obj):
        """
        Метод для сериализации типа доставки
        """
        return obj.delivery.type if obj.delivery else None


# --------       свои адреса   ---------

class UserAddressSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для сериализатора UserAddresses.
    Возможно создание, редактирование, удаление автором.
    """
    coordinates = serializers.CharField(required=False,
                                        allow_null=True,
                                        allow_blank=True,
                                        validators=[coordinates_validator,],
                                        )

    class Meta:
        fields = ('id', 'address', 'coordinates', 'flat', 'floor', 'interfon')
        model = UserAddress
        read_only_fields = ('id',)


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


class CartDishSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для модели CartDish.
    """
    dish = DishShortSerializer(required=True)

    class Meta:
        fields = ('id', 'dish', 'quantity',)
        model = CartDish
        read_only_fields = ('id',)
        #                     'dish', 'unit_price', 'amount')


class PromoCodeField(serializers.RelatedField):
    def to_representation(self, instance):
        return {"promocode": f"{instance.code}",
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
                  # 'promocode', 'discount',
                  # 'discounted_amount',
                  # 'message')
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

    dish = DishShortSerializer(required=True)

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

    city = serializers.CharField(max_length=20, required=True,
                                 validators=[validate_city,])

    payment_type = serializers.CharField(max_length=20,
                                         required=True,
                                         validators=[validate_payment_type,])
    language = LanguageField(required=False, allow_null=True, write_only=True)

    class Meta:
        fields = ('recipient_phone', 'language',
                  'city', 'delivery_time',
                  'orderdishes', 'amount', 'promocode', 'payment_type')
        model = Order

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


class TakeawayOrderWriteSerializer(BaseOrderSerializer):
    status_display = serializers.SerializerMethodField()
    restaurant = serializers.PrimaryKeyRelatedField(
        queryset=Restaurant.objects.filter(is_active=True),
        required=True
    )
    amount = serializers.DecimalField(required=False,
                                      allow_null=True,
                                      max_digits=8,
                                      decimal_places=2)

    class Meta:
        fields = ('order_number', 'created',
                  'status_display',
                  'city', 'delivery_time', 'restaurant',
                  'recipient_name', 'recipient_phone',
                  'amount', 'discounted_amount',
                  'orderdishes',  'promocode',
                  'payment_type', 'comment',
                  'items_qty', 'persons_qty',
                  )
        model = Order
        read_only_fields = ('order_number', 'created',
                            'status'
                            )

    def get_status_display(self, obj):
        # Получаем разъяснение статуса заказа по его значению
        status_display = dict(settings.ORDER_STATUS_CHOICES).get(obj.status)

        return status_display

    def create(self, validated_data):
        request = self.context.get('request')

        user = (request.user.base_profile
                if request.user.is_authenticated else None)

        if 'orderdishes' in validated_data:
            orderdishes = validated_data.pop('orderdishes')

            with transaction.atomic():
                order = Order.objects.create(**validated_data,
                                             user=user,
                                             created_by=1,
                                             admin_edit=False)

                OrderDish.create_orderdishes_from_cartdishes(
                    order, no_cart_cartdishes=orderdishes)

                if order.user:
                    order.user.orders_qty += 1
                    order.user.save(update_fields=['orders_qty'])

                send_message_new_order(order)

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
        rep['total_discount'] = str(
                    Decimal(rep['amount']) - Decimal(rep['discounted_amount']))

        return rep


class TakeawayConditionsSerializer(serializers.ModelSerializer):
    restaurants = SerializerMethodField()

    class Meta:
        fields = ('city', 'restaurants',
                  'discount')
        model = Delivery
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
    coordinates = serializers.CharField(required=False,
                                        allow_blank=True,
                                        allow_null=True,
                                        validators=[coordinates_validator])

    class Meta(BaseOrderSerializer.Meta):
        fields = BaseOrderSerializer.Meta.fields + (
                    'recipient_address', 'my_delivery_address',
                    'coordinates', 'recipient_name', 'comment',
                    'items_qty', 'persons_qty')


class DeliveryOrderWriteSerializer(BaseOrderSerializer):
    status_display = serializers.SerializerMethodField()

    amount = serializers.DecimalField(required=False,
                                      allow_null=True,
                                      max_digits=8,
                                      decimal_places=2)

    class Meta:
        fields = ('order_number', 'created',
                  'status_display',
                  'city', 'delivery_time',
                  'recipient_name', 'recipient_phone',
                  'amount', 'discounted_amount',
                  'orderdishes',  'promocode',
                  'recipient_address',
                  'delivery_cost',
                  'payment_type', 'comment',
                  'items_qty', 'persons_qty',
                  'language'
                  )
        model = Order
        read_only_fields = ('order_number', 'created',
                            'status', 'delivery_cost',
                            )

    def validate_recipient_address(self, value):
        my_address = self.initial_data.get('my_delivery_address')

        if my_address in [None, '']:

            try:
                lat, lon, status = (
                    google_validate_address_and_get_coordinates(value)
                )

            except Exception as e:
                logger.info(
                    'validate_recipient_address'
                    f'recipient_address:{value}, '
                    f'exc:{e}')
                lat, lon = None, None

            self.initial_data['lat'], self.initial_data['lon'] = lat, lon
            self.initial_data['coordinates'] = f"{lat}, {lon}"

        else:
            my_address = UserAddress.objects.filter(id=int(my_address)).first()
            lat, lon = parce_coordinates(my_address.coordinates)
            self.initial_data['coordinates'] = f"{lat}, {lon}"

        return value

    def get_status_display(self, obj):
        # Получаем разъяснение статуса заказа по его значению
        status_display = dict(settings.ORDER_STATUS_CHOICES).get(obj.status)
        return status_display

    def create(self, validated_data):
        request = self.context.get('request')
        lat, lon = parce_coordinates(self.initial_data['coordinates'])
        validated_data['delivery_zone'] = get_delivery_zone(
                self.validated_data.get('city'), lat, lon,
            )

        user = (request.user.base_profile
                if request.user.is_authenticated else None)

        validated_data['coordinates'] = self.initial_data['coordinates']

        address_comment, comment = (
            split_and_get_comment(validated_data['comment']))
        validated_data['address_comment'] = address_comment
        validated_data['comment'] = comment

        if 'orderdishes' in validated_data:
            orderdishes = validated_data.pop('orderdishes')

            with transaction.atomic():
                order = Order.objects.create(**validated_data,
                                             user=user,
                                             created_by=1)

                OrderDish.create_orderdishes_from_cartdishes(
                    order, no_cart_cartdishes=orderdishes)

                if order.user:
                    order.user.orders_qty += 1
                    order.user.save(update_fields=['orders_qty'])

                send_message_new_order(order)
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
        rep['total_discount'] = str(
                    Decimal(rep['amount']) - Decimal(rep['discounted_amount']))
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


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
from delivery_contacts.services import get_delivery_cost_zone
from delivery_contacts.utils import (
    google_validate_address_and_get_coordinates,
    parce_coordinates)
from promos.models import PrivatPromocode, Promocode, PromoNews
from shop.models import (CartDish, Order, OrderDish,
                         ShoppingCart, get_amount, get_promocode_results,
                         get_discount, promocode_vs_discount,
                         current_cash_disc_status)
from shop.validators import (validate_delivery_time, validate_payment_type,
                             validate_city, validate_comment)
from shop.utils import split_and_get_comment
import tm_bot.models as tmbmod
from tm_bot.validators import (get_msgr_data_validated)
from users.models import (BaseProfile, UserAddress, validate_phone_unique,
                          user_add_new_order_data)
from users.validators import (validate_birthdate,
                              validate_first_and_last_name,
                              coordinates_validator, validate_language)
from promos.validators import get_promocode_validate_active_in_timespan
from .services import get_rep_dic
from decimal import Decimal
from tm_bot.services import (send_message_new_order,
                             send_error_message_order_unsaved,
                             send_error_message_order_saved)
from djoser.serializers import UserCreateSerializer
from django.utils.translation import get_language
import logging


logger = logging.getLogger(__name__)


User = get_user_model()
# 'users.WEBAccount'


# ---------------- ЛИЧНЫЙ КАБИНЕТ --------------------


class MessengerAccountSerializer(serializers.ModelSerializer):
    msngr_username = serializers.CharField(required=False, allow_null=True)
    msngr_type = serializers.CharField(required=False, allow_null=True,)

    class Meta:
        model = tmbmod.MessengerAccount
        fields = ('msngr_username', 'msngr_type')

    def to_internal_value(self, data):
        """Проверка заполнены ли все поля, соответствуют ли они требованиям.
        Если все ок, то ищется мессенджер аккаунт (MA) с такими type, username.
        - если MA находится, то он возвращается в основной сериализатор,
        - если МА НЕ находится, то возвращается словарь из type/username.
        """
        msngr_username = data['msngr_username']
        msngr_type = data.get('msngr_type', None)
        if msngr_username == '' and msngr_type is None:
            return {}
        else:
            get_msgr_data_validated(data)
            messenger_account = tmbmod.MessengerAccount.objects.filter(
                msngr_type=msngr_type,
                msngr_username=msngr_username).first()

            if messenger_account is not None:
                return messenger_account

            else:
                return super().to_internal_value(data)


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
    city = serializers.CharField(max_length=20, required=True,
                                 validators=[validate_city,])

    def validate(self, attrs):
        # Вызываем метод validate родительского класса
        # и передаем в него атрибуты attrs
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

    class Meta(UserCreateSerializer.Meta):
        fields = UserCreateSerializer.Meta.fields + (
                    'city',)


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
    )
    first_name = serializers.CharField(
                        validators=[validate_first_and_last_name,])

    last_name = serializers.CharField(
                        validators=[validate_first_and_last_name,])

    phone = PhoneNumberField(required=False)

    city = serializers.CharField(max_length=20, required=True,
                                 validators=[validate_city,])

    class Meta:
        model = User
        fields = ('first_name', 'last_name',
                  'email', 'phone',
                  'date_of_birth',
                  'messenger_account', 'is_subscribed',
                  'city'
                  )
        read_only_fields = ('email', 'date_of_birth')

    def validate_messenger_account(self, value):
        request = self.context['request']
        messenger_account = value
        if isinstance(messenger_account, tmbmod.MessengerAccount):
            base_profile = request.user.base_profile
            if (hasattr(messenger_account, 'profile')
                and
                messenger_account.profile is not None
                and
                    base_profile.messenger_account is not None
                and
                    base_profile == messenger_account.profile):

                value = None
                # значит МА с переданными данными уже существует и привязан
                # к пользователю, пересохранять не нужно

        return value

    def validate(self, attrs):
        request = self.context['request']

        phone = self.initial_data.get('phone')
        if phone:
            phone = self.initial_data['phone']
            validate_phone_unique(phone, request.user)

        return super().validate(attrs)

    def update(self, instance, validated_data):
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
                    'messenger_account', None)

                # if (messenger_account is not None
                #     and not isinstance(
                #         messenger_account, tmbmod.MessengerAccount)):
                #     messenger_account = (
                #         tmbmod.MessengerAccount.fulfill_messenger_account(
                #             base_profile_validated_data.get(
                #                 'messenger_account')
                #         )
                #     )
                if ((instance.base_profile.messenger_account is not None
                     and messenger_account is None)
                        or
                        messenger_account is not None):
                    BaseProfile.base_profile_messegner_account_update(
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
        city = self.context.get('city')
        restaurant = self.context.get('restaurant')
        if data is not None:
            # if restaurant is not None:
            #     restaurant = Restaurant.objects.filter(id=restaurant).first()

            dish = get_dish_validate_exists_active(data, city, restaurant)
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

    city = serializers.CharField(max_length=20, required=True,
                                 validators=[validate_city,])

    class Meta:
        fields = ('id', 'address', 'coordinates', 'flat', 'floor',
                  'interfon', 'city')
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
                  'utensils',
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
                            'utensils'
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


class OrdersBotSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для модели Restaurant, только чтение!
    """

    class Meta:
        fields = ('msngr_type', 'frontend_link', 'name')
        model = tmbmod.OrdersBot
        read_only_fields = ('msngr_type', 'link', 'name')


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
        return obj.get_workhours()


class DeliverySerializer(TranslatableModelSerializer):
    """
    Базовый сериализатор для модели Delivery, только чтение!
    """
    translations = TranslatedFieldsField(shared_model=Delivery)

    class Meta:
        fields = ('type', 'translations', 'image', 'min_time', 'max_time')
        model = Delivery
        read_only_fields = ('city', 'type', 'translations', 'image',
                            'min_time', 'max_time')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['phone'] = None
        if rep.get('type') == 'takeaway':
            del rep['image']

        if rep.get('type') == 'delivery':
            # Получение телефона для ресторана "по умолчанию" в выбранном городе
            restaurant = Restaurant.objects.filter(
                city=instance.city,
                is_default=True).first()

            # Добавление поля phone в представление, если ресторан найден
            if restaurant:
                rep['phone'] = str(restaurant.phone)

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


class ExtendedRestaurantSerializer(RestaurantSerializer):
    dishes = serializers.SerializerMethodField()

    class Meta(RestaurantSerializer.Meta):
        fields = RestaurantSerializer.Meta.fields + ('dishes',)

    def get_dishes(self, obj):
        """Получает список идентификаторов блюд, связанных с рестораном."""
        # Получаем блюда через промежуточную модель RestaurantDishList
        dishes = Dish.objects.filter(restaurantdishlist__restaurant=obj)
        return list(dishes.values_list('article', flat=True))  # Возвращаем список идентификаторов


class OrderDishWriteSerializer(serializers.ModelSerializer):
    """
    Сериализатор для записи Orderdishes в заказ.
    """

    dish = DishShortSerializer(required=True)

    class Meta:
        fields = ('dish', 'quantity')
        model = OrderDish

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Получаем значение города из initial data
        city_value = self.data.get('city')
        restaurant_value = self.data.get('restaurant')

        # Передаем значение города в контекст вложенного сериализатора
        if city_value:
            self.fields['dish'].context.update(
                {'city': city_value,
                 'restaurant': restaurant_value})


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

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     # Получаем значение города из initial data
    #     if self.initial_data:
    #         city_value = self.initial_data.get('city')
    #         restaurant_value = self.initial_data.get('restaurant')

    #     # Передаем значение города в контекст вложенного сериализатора
    #     if city_value:
    #         self.fields['orderdishes'].context.update(
    #             {'city': city_value,
    #              'restaurant': restaurant_value})

    def to_internal_value(self, data):
        # Получаем значение города и ресторана из входных данных
        city_value = data.get('city')
        restaurant_value = data.get('restaurant')

        # Передаем значение города и ресторана в контекст вложенного сериализатора
        if city_value:
            self.fields['orderdishes'].context.update(
                {'city': city_value, 'restaurant': restaurant_value})

        # Теперь вызываем базовую реализацию to_internal_value
        return super().to_internal_value(data)

    def validate_delivery_time(self, value):
        delivery = self.context.get('extra_kwargs', {}).get('delivery')
        self.delivery = delivery

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
        if data.get('orderdishes') in [[], '', None]:
            raise serializers.ValidationError(
                _("No dishes chosen."))

        if data.get('promocode') and data['promocode'].min_order_amount:
            amount = get_amount(items=data.get('orderdishes'))
            if amount < data['promocode'].min_order_amount:
                raise serializers.ValidationError(
                        _(("Promocode doesn't match order amount"
                           "requirements.")))
        # if request.user.is_authenticated:

        #     base_profile, cart, cartdishes, promocode = (
        #         get_base_profile_cartdishes_promocode(request.user)
        #     )
        #     data['base_profile'] = base_profile
        #     data['cart'] = cart
        #     data['cartdishes'] = cartdishes
        #     data['promocode'] = promocode

        data['source'] = '4'
        self.web_account = self.context['request'].user
        data['user'] = None
        if self.web_account.is_authenticated:
            if self.web_account.base_profile:
                data['user'] = self.web_account.base_profile
        data['created_by'] = 1
        data['delivery'] = self.context['extra_kwargs']['delivery']

        return data

    def process(self):
        cart = self.validated_data.get('cart', None)
        # получаем общую сумму товаров
        self.validated_data['amount'] = get_amount(
                                            cart,
                                            self.validated_data['orderdishes'])

        # получаем стоимость доставки
        if self.delivery.type == 'delivery':
            self.process_delivery_calc()
        else:
            self.validated_data['delivery_cost'] = Decimal(0)

        # получаем стоимость товаров + доставка
        self.validated_data['amount_with_shipping'] = (
            self.validated_data['amount']
            + self.validated_data['delivery_cost']).quantize(
                Decimal('0.01'))

        # получаем данные промокода
        self.promocode_data, promocode_disc_am, self.free_delivery = (
            get_promocode_results(self.validated_data['amount_with_shipping'],
                                  self.validated_data['promocode'],
                                  self.context.get('request'),
                                  cart)
        )

        # получаем максимальную скидку на заказ
        max_discount, max_discount_amount, self.fo_status = (
            get_discount(self.validated_data.get('user'),
                         self.validated_data.get('payment_type'),
                         self.delivery,
                         self.validated_data.get('source'),
                         self.validated_data.get('amount_with_shipping'),
                         self.validated_data.get('language'),
                         self.validated_data.get('discount')))

        self.select_promocode_vs_discount(promocode_disc_am,
                                          max_discount,
                                          max_discount_amount)

        self.validated_data['discounted_amount'] = (
            (self.validated_data['amount_with_shipping']
             - self.total_discount_amount)).quantize(
                Decimal('0.01'))
        self.validated_data['final_amount_with_shipping'] = (
            self.validated_data['discounted_amount'])

    def process_delivery_calc(self):
        lat, lon = parce_coordinates(self.initial_data['coordinates'])

        (self.validated_data['delivery_cost'],
         self.validated_data['delivery_zone']) = (
            get_delivery_cost_zone(self.validated_data['city'],
                                   self.validated_data['amount'],
                                   self.validated_data['delivery'],
                                   lat, lon,
                                   # self.free_delivery
                                   )
        )

    def select_promocode_vs_discount(self, promocode_disc_am,
                                     max_discount, max_discount_amount):
        result = promocode_vs_discount(promocode_disc_am,
                                       max_discount_amount)
        if result == {'promo': False, 'max_disc': True}:
            # self.validated_data['promocode'] = None     оставить для статистики
            self.validated_data['promocode_disc_amount'] = Decimal(0)
            self.validated_data['discount'] = max_discount
            self.validated_data['discount_amount'] = max_discount_amount
            self.total_discount_amount = max_discount_amount

        elif result == {'promo': True, 'max_disc': False}:
            self.validated_data['promocode_disc_amount'] = promocode_disc_am
            self.validated_data['discount'] = None
            self.validated_data['discount_amount'] = Decimal(0)
            self.total_discount_amount = promocode_disc_am

    def get_rep_basic(self):
        self.reply_data = {
            'amount': self.validated_data['amount'],
            'promocode': self.promocode_data,
            'total_discount': self.total_discount_amount,
            'first_order': self.fo_status,
            'cash_discount': current_cash_disc_status(),
            'detail': ''
        }

    def get_reply_data_takeaway(self):
        self.process()
        self.get_rep_dic_takeaway()
        return self.reply_data

    def get_rep_dic_takeaway(self):
        self.get_rep_basic()
        self.reply_data.update({
            'total': {
                "title": "Total amount",
                "total_amount": self.validated_data[
                    'final_amount_with_shipping']
                },
        })

    def get_reply_data_delivery(self):
        self.process()
        self.get_rep_basic()
        self.get_rep_dic_delivery()
        return self.reply_data

    def get_rep_dic_delivery(self):
        delivery = self.validated_data['delivery']
        delivery_zone = self.validated_data['delivery_zone']
        if self.instance:
            delivery = self.instance.delivery
            delivery_zone = self.instance.delivery_zone

        if (delivery.type == 'delivery'
                and delivery_zone.name == 'уточнить'):

            if self.instance is None:
                total = self.validated_data['discounted_amount']
            else:
                total = self.instance.discounted_amount

            self.reply_data.update({
                'delivery_cost': 'Requires clarification',
                'total': {
                    'title': 'Total amount, excl. delivery',
                    'total_amount': total
                    }
            })

            if not self.free_delivery:

                self.reply_data['detail'] = (
                    "Delivery address is outside our service area or "
                    "an error occurred while processing the delivery data. "
                    "Please check with the administrator regarding "
                    "the delivery possibility and it's cost."
                )

            else:
                self.reply_data['detail'] = (
                    "Delivery address is outside our service area or "
                    "an error occurred while processing the delivery data. "
                    "Please check with the administrator regarding "
                    "the delivery possibility and free delivery promocode."
                )

        else:
            if self.instance is None:
                total = self.validated_data['discounted_amount']

                self.reply_data['delivery_cost'] = self.validated_data['delivery_cost']

            else:
                total = self.instance.final_amount_with_shipping
                self.reply_data['delivery_cost'] = self.instance.delivery_cost

            self.reply_data['total'] = {
                    "title": "Total amount, incl. delivery",
                    "total_amount": total
                    }

        return self.reply_data


class TakeawayOrderSerializer(BaseOrderSerializer):
    restaurant = serializers.PrimaryKeyRelatedField(
        queryset=Restaurant.objects.filter(is_active=True),
        required=True
    )

    recipient_name = serializers.CharField(
                        validators=[validate_first_and_last_name,])

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

    recipient_name = serializers.CharField(
                        validators=[validate_first_and_last_name,])

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
        self.process()

        if 'orderdishes' in self.validated_data:
            orderdishes = self.validated_data.pop('orderdishes')

            with transaction.atomic():
                order = Order.objects.create(**self.validated_data)

                OrderDish.create_orderdishes_from_cartdishes(
                    order, no_cart_cartdishes=orderdishes)

                if order.user:
                    user_add_new_order_data(order)

                send_message_new_order(order)
                # from tm_bot.handlers.status import send_new_order_notification
                # send_new_order_notification(order.id, order.status)

            # cart = validated_data.pop('cart')
            # cartdishes = validated_data.pop('cartdishes')

            # with transaction.atomic():
            #     order = Order.objects.create(**validated_data,
            #                                  user=user,
            #                                  language=language)

            #     OrderDish.create_orderdishes_from_cartdishes(
            #         order, cartdishes=cartdishes)

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

        return ExtendedRestaurantSerializer(restaurants, many=True).data


class DeliveryOrderSerializer(BaseOrderSerializer):
    coordinates = serializers.CharField(required=False,
                                        allow_blank=True,
                                        allow_null=True,
                                        validators=[coordinates_validator])

    recipient_name = serializers.CharField(
                        validators=[validate_first_and_last_name,])

    comment = serializers.CharField(validators=[validate_comment,])

    class Meta(BaseOrderSerializer.Meta):
        fields = BaseOrderSerializer.Meta.fields + (
                    'recipient_address', 'my_delivery_address',
                    'coordinates', 'recipient_name', 'comment',
                    'items_qty', 'persons_qty')

    def validate_recipient_address(self, value):
        ''' Если координаты изначально даются НЕ перезапрашиваем их.
        Если координат нет, запрашиваем их по адресу.'''

        my_address = self.initial_data.get('my_delivery_address')
        city = self.initial_data.get('city')
        lat, lon = parce_coordinates(
                            self.initial_data.get('coordinates'))

        if my_address in [None, '']:
            if lat is None and lon is None:
                try:
                    lat, lon, status = (
                        google_validate_address_and_get_coordinates(value,
                                                                    city)
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
            if lat is None and lon is None:
                my_address = UserAddress.objects.filter(
                                                id=int(my_address)).first()
                lat, lon = parce_coordinates(my_address.coordinates)
                self.initial_data['coordinates'] = f"{lat}, {lon}"

        return value


class DeliveryOrderWriteSerializer(BaseOrderSerializer):
    status_display = serializers.SerializerMethodField()

    amount = serializers.DecimalField(required=False,
                                      allow_null=True,
                                      max_digits=8,
                                      decimal_places=2)

    recipient_name = serializers.CharField(
                        validators=[validate_first_and_last_name,])

    comment = serializers.CharField(validators=[validate_comment,])

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
                  'language', 'coordinates',
                  )
        model = Order
        read_only_fields = ('order_number', 'created',
                            'status', 'delivery_cost',
                            )

    def validate_recipient_address(self, value):
        ''' Игнорируем передаваемые координаты и принудительно
        перезапрашиваем их по адресу.'''
        my_address = self.initial_data.get('my_delivery_address')
        city = self.initial_data.get('city')
        lat, lon = parce_coordinates(
                            self.initial_data.get('coordinates'))

        if my_address in [None, '']:
            if lat is None and lon is None:
                try:
                    lat, lon, status = (
                        google_validate_address_and_get_coordinates(value,
                                                                    city)
                    )

                except Exception as e:
                    logger.info(
                        'FAIL validate_recipient_address'
                        f'recipient_address:{value}, '
                        f'exc:{e}')
                    lat, lon = None, None

                self.initial_data['lat'], self.initial_data['lon'] = lat, lon
                self.initial_data['coordinates'] = f"{lat}, {lon}"

        else:
            if lat is None and lon is None:
                my_address = UserAddress.objects.filter(
                                                id=int(my_address)).first()
                lat, lon = parce_coordinates(my_address.coordinates)
                self.initial_data['coordinates'] = f"{lat}, {lon}"

        # пере получаем координаты для проверки переданных координат и адреса
        try:
            self.lat_check, self.lon_check, status = (
                        google_validate_address_and_get_coordinates(value,
                                                                    city)
                    )
        except Exception as e1:
            logger.info(
                'FAIL validate_recipient_address check'
                f'recipient_address:{value}, '
                f'exc:{e1}')
            self.initial_data['process_comment'] = (
                f"Не удалось получить координаты для их перепроверки ",
                "при сохранении заказа"
            )
            self.lat_check, self.lon_check = None, None

        return value

    def get_status_display(self, obj):
        # Получаем разъяснение статуса заказа по его значению
        status_display = dict(settings.ORDER_STATUS_CHOICES).get(obj.status)
        return status_display

    def create(self, validated_data):
        # request = self.context.get('request')
        # lat, lon = parce_coordinates(self.initial_data['coordinates'])
        # validated_data['delivery_zone'] = get_delivery_zone(
        #         self.validated_data.get('city'), lat, lon,
        #     )

        # user = (request.user.base_profile
        #         if request.user.is_authenticated else None)

        # validated_data['coordinates'] = self.initial_data['coordinates']

        self.process()
        self.doublecheck_address_coordinates()

        address_comment, comment = (
            split_and_get_comment(validated_data['comment']))
        self.validated_data['address_comment'] = address_comment
        self.validated_data['comment'] = comment

        if 'orderdishes' in self.validated_data:
            orderdishes = self.validated_data.pop('orderdishes')

            with transaction.atomic():
                order = Order.objects.create(**self.validated_data)

                OrderDish.create_orderdishes_from_cartdishes(
                    order, no_cart_cartdishes=orderdishes)

                if order.user:
                    user_add_new_order_data(order)

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

        return order

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['total_discount'] = str(
                    Decimal(rep['amount']) - Decimal(rep['discounted_amount']))
        rep = get_rep_dic(rep, instance=instance)

        return rep

    def doublecheck_address_coordinates(self):
        delivery_cost_check, delivery_zone_check = (
            get_delivery_cost_zone(self.validated_data['city'],
                                   self.validated_data['amount'],
                                   self.validated_data['delivery'],
                                   self.lat_check, self.lon_check,
                                   # self.free_delivery
                                   )
        )
        if delivery_cost_check != self.validated_data['delivery_cost']:
            logger.error(
                "\nFAIL validate_recipient_address/coordinates:\n"
                "RECEIVED and SAVED:\n"
                f"recipient_address: {self.initial_data['recipient_address']}, \n"
                f"coordinates: {self.initial_data['coordinates']}, \n"
                f"delivery_cost: {self.validated_data['delivery_cost']}, \n"
                f"delivery_zone: {self.validated_data['delivery_zone']}, \n"
                "CHECK_RESULTS:\n"
                f"recipient_address: {self.validated_data['recipient_address']}, \n"
                f"coordinates: {self.lat_check}, {self.lon_check}, \n"
                f"delivery_cost: {delivery_cost_check}, \n"
                f"delivery_zone: {delivery_zone_check}, \n"
            )

            process_comment = (
                f"Ошибка проверки координат!\n"
                f"Расчет: {self.initial_data['recipient_address']}, "
                        f"({self.initial_data['coordinates']}), "
                        f"{self.validated_data['delivery_cost']} RSD, "
                        f"{self.validated_data['delivery_zone']}\n"
                f"Проверка: {self.validated_data['recipient_address']}, "
                            f"({self.lat_check}, {self.lon_check}), "
                            f"{delivery_cost_check} RSD, "
                            f"{delivery_zone_check}\n"
            )

            self.validated_data['process_comment'] = (
                self.validated_data.get('process_comment', '')
                + process_comment)


class DeliveryConditionsSerializer(serializers.ModelSerializer):
    dishes = SerializerMethodField()

    class Meta:
        fields = ('city', 'min_order_amount',
                  'min_time', 'max_time',
                  'default_delivery_cost',
                  'discount', 'dishes')
        model = Delivery
        read_only_fields = ('city', 'min_order_amount',
                            'min_time', 'max_time',
                            'default_delivery_cost',
                            'discount', 'dishes')

    def get_dishes(self, delivery: Delivery) -> QuerySet[dict]:
        """Получает список блюд активных в городе.

        Args:
            delivery (Delivery): Запрошенный объект доставки.

        Returns:
            QuerySet[dict]: Список блюд в городе.
        """
        city = delivery['city']
        dishes = Dish.objects.filter(citydishlist__city=city)
        return list(dishes.values_list('article', flat=True))  # Получаем список идентификаторов


class BotOrderSerializer(serializers.ModelSerializer):
    """При сохранении заказа бот н аплатформе сам отправляет сообщения
    в админский чат."""
    class Meta:
        fields = '__all__'
        model = Order

    def to_internal_value(self, data):
        process_comment = ''
        try:
            context = self.context.get('extra_kwargs')
            bot = context.get('bot')
            city = bot.city
            # ресторан сохранится по дефолту для города
            orderdishes, amount, items_qty, process_comment1 = (
                tmbmod.get_orderdishes_tmbot(self, data))

            (delivery, delivery_zone, coordinates,
             delivery_cost, address, process_comment2) = (
                            tmbmod.get_delivery_data_tmbot(self, data,
                                                           city, amount))

            msngr_account, user_telegram_data, process_comment3 = (
                tmbmod.get_tm_user(self, data))
            # promocode = get_promocode_tmbot(self, data)

            delivery_time, time_comment, process_comment4 = (
                tmbmod.get_time_tmbot(data.get("time")))

            if (time_comment in ['', None]
                    and data.get('comment') not in ['', None]):
                comment = f"{data.get('comment')}"

            elif (data.get('comment') in ['', None]
                    and time_comment not in ['', None]):
                comment = f"{time_comment}."

            else:
                comment = f"{time_comment}. {data.get('comment')}"

            process_comment = (process_comment1 + process_comment2
                               + process_comment3 + process_comment4)
            if process_comment == '':
                process_comment = None

            with transaction.atomic():
                if msngr_account is None:
                    msngr_account = tmbmod.MessengerAccount.objects.create(
                        **user_telegram_data,
                        msngr_type='tm'
                    )
                user = None
                if msngr_account.registered:
                    user = msngr_account.profile

                order = Order.objects.create(
                    source_id=int(data.get('id')),
                    recipient_name=data.get("recipient"),
                    recipient_phone=data.get("mobile"),
                    recipient_address=address,
                    city=city,
                    delivery=delivery,
                    delivery_time=delivery_time,
                    delivery_zone=delivery_zone,
                    coordinates=coordinates,
                    delivery_cost=delivery_cost,
                    msngr_account=msngr_account,
                    created_by=1,
                    user=user,
                    source='3',
                    comment=comment,
                    process_comment=process_comment,
                    items_qty=items_qty,                   #!!!!!!!!!!!!!!!!!!!!!!!!!!
                    # оплата?
                )
                OrderDish.create_orderdishes_from_cartdishes(
                        order, no_cart_cartdishes=orderdishes)

                if order.user:
                    user_add_new_order_data(order)

                logger.info(f'Bot order #{order.source_id} saved under #{order.id}')

                if order.process_comment:
                    try:
                        send_error_message_order_saved(order)
                    except Exception as exep:
                        logger.error(
                            f"Message of error save TM order #{data.get('id')}"
                            f"isn't sent. {exep}.")

        except Exception as e:
            logger.error(f"Bot order #{data.get('id')} isn't saved. {e}.")
            try:
                send_error_message_order_unsaved(bot, data.get('id'), e)
            except Exception as exep:
                logger.error(
                    f"Message of unsave TM order #{data.get('id')} "
                    f"isn't sent. {exep}.")

        return {}

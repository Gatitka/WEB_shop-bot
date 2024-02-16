import base64  # Модуль с функциями кодирования и декодирования base64
import re
from datetime import date, datetime

import phonenumbers
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
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
from shop.models import CartDish, Order, OrderDish, ShoppingCart
from tm_bot.models import MessengerAccount
from users.models import BaseProfile, UserAddress

User = get_user_model()


# ---------------- ЛИЧНЫЙ КАБИНЕТ --------------------
class MessengerAccountSerializer(serializers.ModelSerializer):
    msngr_phone = PhoneNumberField

    class Meta:
        model = MessengerAccount
        fields = ('msngr_username', 'msngr_type', 'msngr_phone')

    def validate_msngr_phone(self, value):
        """
        Пользовательская валидация для номера телефона.
        """
        if value:
            try:
                parsed_phone = phonenumbers.parse(value, None)
                if not phonenumbers.is_valid_number(parsed_phone):
                    raise serializers.ValidationError(
                        "Неверный формат номера телефона.")
            except Exception:
                raise serializers.ValidationError(
                    "Неверный формат номера телефона.")

        return value

    def validate(self, data: dict) -> dict:
        """
        Проверка данных в поле Messenger_account.
        Если телеграмм, то ID wbahjdjt
        """
        msngr_type = data.get('msngr_type')
        msngr_username = data.get('msngr_username')

        if msngr_type:
            if msngr_username:

                if msngr_type == 'tm':
                    # Проверка на допустимые символы
                    # (A-z, 0-9, и подчеркивания)
                    if not re.match("^@[A-Za-z0-9_]+$", msngr_username):
                        raise serializers.ValidationError(
                            "Недопустимые символы в Telegram username."
                            " Username должен начинаться с @ и содержать "
                            "только цифры и буквы."
                        )

                    # Проверка длины (5-32 символа)
                    if not (5 <= len(msngr_username) <= 32):
                        raise serializers.ValidationError(
                            "Длина Telegram username должна быть"
                            " от 5 до 32 символов."
                        )

                elif msngr_type == 'wts':
                    # метод validate наступает после метода
                    # validate_msngr_phone. Раз на том этапе не было ошибок
                    # валидации, то номер телефона корректен и его можно
                    # сохранить в username WtsApp.
                    pass

                else:
                    raise ValidationError("Сейчас присоединяем только tm, wts.")

        return data


class MyUserSerializer(serializers.ModelSerializer):
    date_of_birth = SerializerMethodField(required=False)
    messenger = SerializerMethodField(required=False)
    email = serializers.EmailField(validators=[EmailValidator()])
    phone = PhoneNumberField(required=True)

    class Meta:
        model = User
        fields = ('first_name', 'last_name',
                  'email', 'phone',
                  'date_of_birth',
                  'web_language',
                  'messenger',
                  )
        read_only_fields = ('email',)

    def get_date_of_birth(self, user: User):
        """Получает значение, если авторизованный пользователь имеет
        этот рецепт в корзине покупок.
        Args:
            dish (Dish): Запрошенное блюдо.
        Returns:
            bool: в корзине покупок или нет.
        """
        if user.is_authenticated:
            date_of_birth = user.base_profile.date_of_birth
        if date_of_birth:
            return date_of_birth.strftime("%d.%m.%Y")
        return None

    def get_messenger(self, user: User) -> MessengerAccount:
        """Получаем значение аккаунта мессенджера
        Args:
            user (User): Запрошенный пользователь.
        Returns:
            MessengerAccount: данные мессенджер-аккаунта (username, type).
        """
        if user.is_authenticated:

            try:
                messenger_account = MessengerAccount.objects.get(
                    profile=user.base_profile
                )
                serializer = MessengerAccountSerializer(messenger_account)
                return serializer.data

            except MessengerAccount.DoesNotExist:
                messenger_account = None
                return None

    def validate_first_name(self, value):
        if (not value
            or value in ['me', 'i', 'я', 'ja', 'и']
                or (value.isalpha() is not True)):

            raise serializers.ValidationError(
                {'first_name': ("Please provide first_name. "
                                "Only letters are allowed.")})
        return value

    def validate(self, data: dict) -> dict:
        """
        Проверка данных в поле Messenger_account, date_of_birth.
        """
        if 'messenger' in self.initial_data:
            messenger = self.initial_data.get('messenger')

            if messenger:
                if isinstance(messenger, dict):
                    if 'msngr_type' not in messenger:
                        raise serializers.ValidationError(
                            "Ключа msngr_type нет в передаваемом словаре messenger.")
                    if 'msngr_username' not in messenger:
                        raise serializers.ValidationError(
                            "Ключа msngr_username нет в передаваемом словаре messenger.")

                    if (messenger['msngr_type'] is not None
                            and messenger['msngr_username'] is not None):

                        if messenger['msngr_type'] == 'tm':
                            messenger['msngr_phone'] = None
                        elif messenger['msngr_type'] == 'wts':
                            messenger['msngr_phone'] = messenger['msngr_username']
                        else:
                            raise serializers.ValidationError(
                                "msngr_type принимается только 'tm', 'wts'."
                            )

                        serializer = MessengerAccountSerializer(data=messenger)
                        if not serializer.is_valid():
                        # Если данные не прошли валидацию, обработайте ошибки, если нужно
                            raise serializers.ValidationError(serializer.errors)
                    else:
                        messenger = None

                else:
                    raise serializers.ValidationError(
                        "объект messenger не является словарем")

        if 'date_of_birth' in self.initial_data:
            date_of_birth = self.initial_data.get('date_of_birth')

            if date_of_birth:
                try:
                    date_obj = datetime.strptime(
                        date_of_birth, "%d.%m.%Y"
                    ).date()
                    today = date.today()

                    if date_obj > today:
                        raise serializers.ValidationError({
                            "date_of_birth": ("Дата рождения "
                                              "не может быть в будущем.")
                        })
                    data['date_of_birth'] = date_obj

                except ValueError:
                    raise serializers.ValidationError({
                        "date_of_birth": ("Проверьте корректность "
                                          "и формат даты: ДД.ММ.ГГГГ.")
                    })

            else:
                data['date_of_birth'] = None


            data['messenger'] = messenger

        return data

    def update(self, instance: User, validated_data: dict) -> User:
        """
        Метод для редакции данных пользователя.
        Args:
            instance (User): изменяемый рецепт
            validated_data (dict): проверенные данные из запроса.
        Returns:
            User: созданный рецепт.
        """
        if 'messenger' in validated_data:
            messenger = validated_data.pop('messenger')

            if instance.base_profile.messenger_account:
                if messenger is None:
                    msngr_account = instance.base_profile.messenger_account
                    instance.base_profile.messenger_account = None
                    instance.base_profile.save(
                        update_fields=['messenger_account']
                    )
                    msngr_account.delete()

                else:
                    instance.base_profile.messenger_account.save(
                        msngr_type=messenger['msngr_type'],
                        msngr_username=messenger['msngr_username'],
                        msngr_phone=messenger['msngr_phone'],
                    )

            else:
                if messenger:
                    messenger_account, created = MessengerAccount.objects.get_or_create(
                        msngr_type = messenger.get('msngr_type'),
                        msngr_username = messenger.get('msngr_username'),
                    )
                    if created:
                        messenger_account.msngr_phone = messenger.get('msngr_phone')
                        messenger_account.language = instance.web_language
                        messenger_account.save()


                    instance.base_profile.messenger_account = messenger_account
                    instance.base_profile.save(
                        update_fields=['messenger_account']
                    )

        if 'date_of_birth' in validated_data:
            date_of_birth = validated_data.pop('date_of_birth')

            instance.base_profile.date_of_birth = date_of_birth

            instance.base_profile.save(
                update_fields=['date_of_birth']
            )

        email_field = get_user_email_field_name(User)
        if email_field in validated_data:
            if settings.DJOSER['SEND_ACTIVATION_EMAIL']:
                instance_email = get_user_email(instance)
                if instance_email != validated_data[email_field]:
                    instance.is_active = False
                    instance.save(update_fields=["is_active"])

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
        fields = ('translations', 'image')
        model = Dish

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        translations = rep['translations']
        for lang, translation in translations["translations"].items():
            if "msngr_short_name" in translation:
                del translation["msngr_short_name"]
            if "msngr_text" in translation:
                del translation["msngr_text"]
        return rep


class OrderDishesShortSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для Order_dishes.
    Возможно только чтение.
    """
    dish = DishShortSerializer()

    class Meta:
        fields = ('dish', 'quantity', 'amount')
        model = OrderDish


class UserOrdersSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для Orders.
    Возможно только чтение.
    """
    order_dishes = OrderDishesShortSerializer(many=True)
    status = serializers.CharField(source='get_status_display')

    class Meta:
        fields = ('id', 'created', 'status',
                  'order_dishes', 'final_amount_with_shipping')
        model = Order
        read_only_fields = ('id', 'created', 'status',
                            'order_dishes', 'final_amount_with_shipping')

    def get_orer_dishes(self, order: Order) -> QuerySet[dict]:
        """Получает список блюд заказа.

        Args:
            order (Order): Запрошенный заказ.

        Returns:
            QuerySet[dict]: Список блюд в заказе.
        """
        return order.order_dishes.values(
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
        fields = ('id', 'priority', 'translations', 'slug',)
        model = Category
        read_only_fields = ('id', 'priority', 'translations', 'slug',)


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
        fields = ('id', 'priority',
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
        read_only_fields = ('id', 'priority',
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

    class Meta:
        fields = ('id', 'short_name',
                  'city', 'address', 'coordinates',
                  'work_hours', 'phone',
                  'image')
        model = Restaurant
        read_only_fields = ('id', 'short_name',
                            'city', 'address', 'coordinates',
                            'work_hours', 'phone',
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
        fields = ('id', 'translations',
                  'image')
        model = Dish
        read_only_fields = ('id', 'translations',
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
        read_only_fields = ('id', 'num_of_items',
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

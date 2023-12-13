from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework.serializers import SerializerMethodField
from django.db.models import F, QuerySet
from catalog.models import Dish, Category
from shop.models import ShoppingCart, CartDish, Delivery, Order, OrderDish, Shop
from users.models import BaseProfile, UserAddress

User = get_user_model()



class UserOrdersSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для сериализатора Orders.
    Возможно только чтение создание.
    """
    dishes = SerializerMethodField()

    class Meta:
        fields = ('id', 'created', 'status', 'dishes', 'amount')
        model = Order

    def get_dishes(self, order: Order) -> QuerySet[dict]:
        """Получает список блюд заказа.

        Args:
            order (Order): Запрошенный заказ.

        Returns:
            QuerySet[dict]: Список блюд в заказе.
        """
        return order.dishes.values(
            'id',
            'short_name_rus',
            quantity=F('orders__quantity'),
            # amount=F('orders__amount')
        )


class DishShortSerializer(serializers.ModelSerializer):
    """
    Сериализатор для краткого отображения блюд.
    """
    # image = Base64ImageField()

    class Meta:
        fields = ('id', 'short_name_rus', 'price',
                  'text_rus', 'category')  # 'image'
        model = Dish
        read_only_fields = ('id', 'short_name_rus',
                            'price', 'text_rus', 'category')  # 'image'


class ShopSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для модели Shop, только чтение!
    """

    class Meta:
        fields = ('id', 'short_name', 'address_rus', 'address_en',
                  'address_srb', 'work_hours',
                  'phone', 'is_active')
        model = Shop
        read_only_fields = ('id', 'short_name', 'address_rus', 'address_en',
                            'address_srb', 'work_hours',
                            'phone', 'is_active')


class DeliverySerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для модели Delivery, только чтение!
    """

    class Meta:
        fields = ('id', 'city', 'description_rus', 'description_en',
                  'description_srb')
        model = Delivery
        read_only_fields = ('id', 'city', 'description_rus', 'description_en',
                  'description_srb')


class UserAddressSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для сериализатора UserAddresses.
    Возможно создание, редактирование, удаление автором.
    """
    class Meta:
        fields = ('id', 'city', 'short_name', 'full_address', 'type')
        model = UserAddress
        read_only_fields = ('id',)

    # если не писать кастомной валидации, то по умолчанию и так просиходит валидация обязательных полей
    # def validate(self, data: dict) -> dict:
    #     city = data['city']
    #     if city is None:
    #         raise serializers.ValidationError(
    #             "Выберите город."
    #         )
    #     return data





# class WebAccauntSerializer(serializers.ModelSerializer):
#     """
#     Базовый сериализатор для модели WebAccount.
#     Все поля обязательны.
#     """

#     class Meta:
#         fields = ('id', 'email', 'first_name',
#                   'last_name')
#         model = User


# class SignUpSerializer(WebAccauntSerializer):
#     """
#     Сериализатор для регистрации нового пользователя.
#     Все поля обязательны.
#     Валидация:
#      - Если в БД есть пользователи с переданными email,
#     вызывается ошибка.
#      - Если имя пользователя - me, вызывается ошибка.
#     """
#     email = serializers.EmailField(
#         max_length=254,
#         required=True
#     )
#     password = serializers.CharField(
#         write_only=True,
#         required=True,
#         max_length=150,
#         min_length=8
#     )   # забрать валидацию из стандарта django
#     first_name = serializers.CharField(
#         write_only=True,
#         required=True,
#         max_length=150,
#         min_length=8
#     )

#     class Meta:
#         fields = ('id', 'email', 'first_name',
#                   'last_name', 'password')
#         read_only_fields = ('id',)
#         model = User

#     def validate(self, data: dict) -> dict:
#         email = data['email']
#         password = data['password']
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

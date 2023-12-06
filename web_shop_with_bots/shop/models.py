from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MinLengthValidator
from catalog.models import Dish
from users.models import BaseProfile
from django.db.models import Sum
from django.conf import settings # для импорта валюты

User = get_user_model()

DELIVERY_CHOICES = (
    ("1", "Доставка"),
    ("2", "Самовывоз")
)

# List of order statuses

WAITING_CONFIRMATION = "WCO"
INAVAILABLE = "INA"
CONFIRMED = "CFD"
DELETED = "DEL"
PAID = "PYD"
RETURNED = "RTN"
READY = "RDY"
HANDLED_TO_DELIVERER = "HDY"
DELIVERED = "DLD"
CLOSED = "CLD"

ORDER_STATUS_CHOICES = (
    (WAITING_CONFIRMATION, "ожидает подтверждения"),
    (INAVAILABLE, "недоступен"),
    (CONFIRMED, "подтвержден"),
    (PAID, "оплачен"),
    (RETURNED, "оформлен возврат"),
    (READY, "готов"),
    (HANDLED_TO_DELIVERER, "передан в доставку"),
    (DELIVERED, "доставлен"),
    (CLOSED, "выдан")
)


class ShoppingCart(models.Model):
    """ Модель для добавления блюд в корзину покупок."""
    user = models.OneToOneField(
        BaseProfile,
        on_delete=models.CASCADE,
        primary_key=True,
        verbose_name='Клиент',
        related_name='shopping_cart',
    )
    dishes = models.ManyToManyField(
        Dish,
        through='CartDish',
        # related_name='dish',
        verbose_name='Товары в заказе',
        help_text='Добавьте блюда в заказ.'
    )   # нужен ли вообще?
    created = models.DateTimeField(
        'Дата добавления', auto_now_add=True
    )
    complited = models.BooleanField(default=False)
    session_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    amount = models.CharField(
        max_length=9,
        default=0
    )
    items_num = models.PositiveSmallIntegerField(
        verbose_name='Кол-во',
        default=0
    )

    @property
    def num_of_items(self):
        itemsqty = self.cart_dishes.aggregate(qty=Sum('quantity'))
        return itemsqty['qty']
    num_of_items.fget.short_description = 'Кол-во'

    @property
    def total_amount(self):
        total_amount = self.cart_dishes.select_related(
            'dish'
            ).annotate(
                item_amount=Sum('dish__price')*Sum('quantity')
                ).aggregate(total_amount=Sum('item_amount'))
        return total_amount['total_amount']
    total_amount.fget.short_description = 'Итого'

    class Meta:
        ordering = ['-created']
        verbose_name = 'корзина покупок'
        verbose_name_plural = 'корзины покупок'

    def __str__(self):
        return f'{self.user} -> корзина id={self.pk}'


class CartDish(models.Model):
    """ Модель для сопоставления связи корзины и блюд."""
    dish = models.ForeignKey(
        Dish,
        on_delete=models.CASCADE,
        related_name='in_shopping_carts',
        verbose_name='Товары в корзине'
    )
    cart = models.ForeignKey(
        ShoppingCart,
        on_delete=models.PROTECT,
        verbose_name='Заказ',
        related_name='cart_dishes',
    )
    quantity = models.PositiveSmallIntegerField(
        verbose_name='Кол-во',
        validators=[MinValueValidator(1)],
        default=1
    )

    @property
    def amount(self):
        return self.dish.price*self.quantity

    class Meta:
        ordering = ['cart']
        verbose_name = 'корзина-блюдо'
        verbose_name_plural = 'корзина-блюдо'
        constraints = [
            models.UniqueConstraint(
                fields=['dish', 'cart'],
                name='unique_dish_cart'
            )
        ]

    def __str__(self):
        return f'корзина id={self.id} -> {self.dish}'


class Delivery(models.Model):
    name_rus = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name='Название РУС'
    )
    name_srb = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name='Название SRB'
    )
    name_en = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name='Название EN'
    )
    type = models.CharField(
        max_length=1,
        verbose_name="тип",
        choices=DELIVERY_CHOICES
    )
    is_active = models.BooleanField(
        default=False
    )
    price = models.FloatField(    # цена
        verbose_name='цена',
        # validators=[MinValueValidator(0.01)]
        null=True,
        blank=True
    )
    min_price = models.FloatField(    # мин цена заказа
        verbose_name='min_цена_заказа',
        # validators=[MinValueValidator(0.01)]
        null=True,
        blank=True
    )
    description_rus = models.CharField(
        max_length=400,
        verbose_name='Описание РУС',
        null=True,
        blank=True
    )
    description_srb = models.CharField(
        max_length=400,
        verbose_name='Описание SRB',
        null=True,
        blank=True
    )
    description_en = models.CharField(
        max_length=400,
        verbose_name='Описание EN',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'доставка'
        verbose_name_plural = 'доставка'

    def __str__(self):
        return f'{self.name_rus}'


class Order(models.Model):
    """ Модель для заказов."""
    created = models.DateTimeField(
        'Дата добавления', auto_now_add=True
    )
    user = models.ForeignKey(
        BaseProfile,
        on_delete=models.CASCADE,
        verbose_name='Клиент',
        related_name='orders',
    )
    dishes = models.ManyToManyField(
        Dish,
        through='OrderDish',
        # related_name='dish',
        verbose_name='Товары в заказе',
        help_text='Добавьте блюда в заказ.'
    )
    status = models.CharField(
        max_length=3,
        verbose_name="Статус",
        choices=ORDER_STATUS_CHOICES,
        default=WAITING_CONFIRMATION
    )
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='доставка'
    )
    # payment
    # promocode
    recipient_name = models.CharField(
        max_length=400,
        verbose_name='получатель'
    )
    recipient_phone = models.CharField(
        verbose_name='Телефон',
        max_length=100,
        validators=[MinLengthValidator(8)],
        blank=True,
        null=True,
        default=None
    )
    recipient_address = models.CharField(
        verbose_name='адрес',
        max_length=200
    )
    time = models.CharField(
        verbose_name='время',
        max_length=100
    )   # настроить форматирование вносимых данных
    comment = models.CharField(
        max_length=400,
        verbose_name='Комментарий',
        help_text='Комментарий к заказу.',
        blank=True,
        null=True
    )
    shop = models.ForeignKey(
        'Shop',
        on_delete=models.CASCADE,
        verbose_name='точка',
        related_name='заказы',
        blank=True,
        null=True,
        default=1
    )

    @property
    def total_amount(self):
        """  CONSIDER PROMOCODE DICOUNT!!!!!"""
        total_amount = self.order_dishes.select_related(
            'dish'
            ).annotate(
                item_amount=Sum('dish__price')*Sum('quantity')
                ).aggregate(total_amount=Sum('item_amount'))
        return total_amount['total_amount']

    total_amount.fget.short_description = 'Итого'

    class Meta:
        ordering = ['-created']
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'

    def __str__(self):
        return f'{self.id}'


class OrderDish(models.Model):
    """ Модель для сопоставления связи заказа и блюд."""
    dish = models.ForeignKey(
        Dish,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='Товары в заказе'
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        verbose_name='Заказ',
        related_name='order_dishes',
    )
    quantity = models.PositiveSmallIntegerField(
        verbose_name='Кол-во',
        validators=[MinValueValidator(1)]
    )

    @property
    def amount(self):
        return self.dish.price*self.quantity

    class Meta:
        ordering = ['dish']
        verbose_name = 'заказ-блюдо'
        verbose_name_plural = 'заказ-блюдо'
        constraints = [
            models.UniqueConstraint(
                fields=['dish', 'order'],
                name='unique_dish_order'
            )
        ]


class Shop(models.Model):
    """ Модель для магазина."""
    short_name = models.CharField(
        max_length=20,
        verbose_name='название'
    )
    address_rus = models.CharField(
        max_length=200,
        verbose_name='описание_РУС'
    )
    address_en = models.CharField(
        max_length=200,
        verbose_name='описание_EN'
    )
    address_srb = models.CharField(
        max_length=200,
        verbose_name='описание_SRB'
    )
    work_hours = models.CharField(
        max_length=100,
        verbose_name='время работы'
    )
    phone = models.CharField(
        max_length=100,
        verbose_name='телефон'
    )
    admin = models.CharField(
        max_length=100,
        verbose_name='админ',
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        default=False
    )
    # map_location = картинка карты

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return f'{self.short_name}'

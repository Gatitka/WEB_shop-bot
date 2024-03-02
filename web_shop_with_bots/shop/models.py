from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import (MaxValueValidator, MinLengthValidator,
                                    MinValueValidator)
from django.db import models

from phonenumber_field.modelfields import PhoneNumberField

from catalog.models import Dish
from delivery_contacts.models import Delivery, DeliveryZone, Restaurant
from promos.models import Promocode
from users.models import BaseProfile
from .validators import validate_order_time
from exceptions import NoDeliveryDataException
from django.core.exceptions import ValidationError
from users.validators import validate_first_and_last_name
from django.shortcuts import get_object_or_404
from datetime import date, datetime, timedelta
from django.db.models import Max, Sum


User = get_user_model()


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
import logging

logger = logging.getLogger(__name__)

class ShoppingCart(models.Model):
    """ Модель для добавления блюд в корзину покупок."""
    user = models.OneToOneField(
        BaseProfile,
        on_delete=models.CASCADE,
        verbose_name='ID клиента',
        related_name='shopping_cart',
        help_text="Поиск в поле по имени и номеру телефона.",
        blank=True, null=True
    )
    device_id = models.CharField(
        max_length=100,
        verbose_name='ID устройства',
        blank=True, null=True
    )
    created = models.DateTimeField(
        'Дата добавления',
        auto_now_add=True
    )
    dishes = models.ManyToManyField(
        Dish,
        through='CartDish',
        related_name='shopping_carts',
        verbose_name='Товары в корзине'
    )
    complited = models.BooleanField(
        verbose_name='Заказана',
        default=False
    )
    amount = models.DecimalField(
        verbose_name='Сумма, DIN',
        help_text="Посчитается автоматически.",
        default=0.00,
        blank=True,
        max_digits=10, decimal_places=2
    )
    promocode = models.ForeignKey(
        Promocode,
        verbose_name='Промокод',
        null=True, blank=True,
        on_delete=models.SET_NULL
    )
    discount = models.DecimalField(
        verbose_name='Скидка, DIN',
        default=0.00,
        null=True,
        max_digits=6, decimal_places=2
    )
    discounted_amount = models.DecimalField(
        verbose_name='Итог сумма, DIN',
        help_text="Посчитается автоматически.",
        default=0.00,
        blank=True,
        max_digits=10, decimal_places=2
    )

    items_qty = models.PositiveSmallIntegerField(
        verbose_name='Кол-во порций, шт',
        default=0,
        blank=True,
        help_text="Посчитается автоматически.",
    )

    class Meta:
        ordering = ['-created']
        verbose_name = 'корзина покупок'
        verbose_name_plural = 'корзины покупок'

    def __str__(self):
        return f'{self.user} -> корзина id={self.pk}'

    def calculate_discounted_amount(self):
        """
        Рассчитывает discounted_amount с учетом скидки от промокода.
        """
        if self.promocode:
            # Если есть промокод, применяем скидку
            self.discount = Decimal(self.amount) * Decimal(self.promocode.discount) / Decimal(100)
            self.discounted_amount = Decimal(self.amount) - self.discount
        else:
            # Если нет промокода и вручную внесенной скидки, final_amount равен общей сумме
            self.discounted_amount = self.amount

    def save(self, *args, **kwargs):
        """
        Переопределяем метод save для автоматического рассчета final_amount перед сохранением.
        """
        self.calculate_discounted_amount()
        if self.pk is None:  # Создание нового объекта
            self.items_qty = 0
        else:
            itemsqty = self.cartdishes.aggregate(qty=Sum('quantity'))
            self.items_qty = itemsqty['qty'] if itemsqty['qty'] is not None else 0
        super().save(*args, **kwargs)

    def empty_cart(self, *args, **kwargs):
        self.dishes.clear()  # Очищаем связанные товары
        self.amount = 0.00
        self.promocode = None
        self.discount = 0.00
        self.discounted_amount = 0.00
        self.items_qty = 0
        self.save()

    @staticmethod
    def get_base_profile_and_shopping_cart(user):
        base_profile = BaseProfile.objects.filter(
                        web_account=user
                    ).select_related(
                        'shopping_cart'
                    ).prefetch_related(
                        'shopping_cart__cartdishes'
                    ).first()

        if base_profile and base_profile.shopping_cart:
            cart = base_profile.shopping_cart
        else:
            cart = None
        return base_profile, cart


class CartDish(models.Model):
    """ Модель для сопоставления связи корзины и блюд."""
    dish = models.ForeignKey(
        Dish,
        on_delete=models.SET_NULL,
        related_name='cartdishes',
        verbose_name='Товары в корзине *',
        help_text="Начните писать название блюда...",
        null=True,
    )
    cart = models.ForeignKey(
        ShoppingCart,
        on_delete=models.SET_NULL,
        verbose_name='Заказ',
        related_name='cartdishes',
        null=True,
    )
    quantity = models.PositiveSmallIntegerField(
        verbose_name='Кол-во *',
        help_text="Внесите колличество.",
        validators=[MinValueValidator(1)],
        default=1
    )
    unit_price = models.DecimalField(
        verbose_name='Цена за ед-цу, DIN.',
        help_text='Подтянется автоматически.',
        default=0.00,
        null=True, blank=True,
        max_digits=6, decimal_places=2
    )
    amount = models.DecimalField(
        verbose_name='Стоимость всей позиции, DIN.',
        help_text="Посчитается автоматически.",
        default=0.00,
        blank=True,
        max_digits=7, decimal_places=2
    )
    dish_article = models.PositiveSmallIntegerField(
        verbose_name='Запись блюда в БД',
        help_text="Подтянется автоматически.",
        null=True, blank=True,
    )
    cart_number = models.PositiveSmallIntegerField(
        verbose_name='Запись корзины в БД',
        help_text="Подтянется автоматически.",
        null=True, blank=True,
    )
    base_profile = models.PositiveSmallIntegerField(
        verbose_name='Запись baseprofile в БД',
        help_text="Подтянется автоматически.",
        null=True, blank=True,
    )


    class Meta:
        ordering = ['cart']
        verbose_name = 'связь корзина-блюдо'
        verbose_name_plural = 'связи корзина-блюдо'
        constraints = [
            models.UniqueConstraint(
                fields=['dish', 'cart'],
                name='unique_dish_cart'
            )
        ]

    def __str__(self):
        return f'корзина id={self.cart.pk} <- {self.dish}'

    def save(self, *args, **kwargs):
        self.amount = Decimal(self.dish.final_price * self.quantity)
        self.unit_price = self.dish.final_price
        self.dish_article = self.dish.pk
        self.cart_number = self.cart.pk
        self.base_profile = self.cart.user.pk

        super(CartDish, self).save(*args, **kwargs)
        self.update_shopping_cart()

    def delete(self, *args, **kwargs):
        super(CartDish, self).delete()
        total_amount = CartDish.objects.filter(
            cart=self.cart
                ).aggregate(ta=Sum('amount'))['ta']

        self.cart.amount = total_amount if total_amount is not None else 0
        self.update_shopping_cart()

    def update_shopping_cart(self, *args, **kwargs):
        cart_dish_agr = CartDish.objects.filter(
            cart=self.cart
        ).aggregate(
            ta=Sum('amount'),
            iq=Sum('quantity'))
        self.cart.amount = (cart_dish_agr['ta'] if
                            cart_dish_agr['ta'] is not None
                            else Decimal(0)
                            )
        self.cart.items_qty = (cart_dish_agr['iq'] if
                               cart_dish_agr['iq'] is not None
                               else 0
                               )
        self.cart.save(update_fields=['amount', 'discounted_amount', 'items_qty'])


class Order(models.Model):
    """ Модель для заказов."""
    order_number = models.IntegerField(
        verbose_name='Номер заказа',
        help_text="Проставится автоматически.",
        blank=True, null=True
    )
    user = models.ForeignKey(
        BaseProfile,
        on_delete=models.PROTECT,
        help_text="Поиск по имени и номеру телефона.",
        verbose_name='Клиент',
        related_name='orders',
        blank=True, null=True
    )
    device_id = models.CharField(
        max_length=100,
        blank=True, null=True
    )
    created = models.DateTimeField(
        'Дата добавления',
        auto_now_add=True
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
        verbose_name='доставка *'
    )
    delivery_db = models.CharField(
        max_length=10,
        verbose_name='доставка запись в бд',
        blank=True, null=True
    )
    delivery_zone = models.ForeignKey(
        DeliveryZone,
        on_delete=models.PROTECT,
        verbose_name='зона доставки',
        blank=True, null=True
    )
    delivery_zone_db = models.CharField(
        max_length=10,
        verbose_name='зона доставки запись в бд',

        blank=True, null=True
    )
    delivery_cost = models.DecimalField(
        verbose_name='стоимость доставки',
        help_text="Посчитается автоматически. Для доставки будет +, для самовывоза -.",
        default=0.00,
        max_digits=7, decimal_places=2,
        blank=True, null=True,
    )
    payment_type = models.CharField(
        max_length=20,
        verbose_name="способ оплаты *",
        choices=settings.PAYMENT_METHODS
    )
    recipient_name = models.CharField(
        max_length=400,
        verbose_name='имя получателя *',
        validators=[validate_first_and_last_name,]
    )
    recipient_phone = PhoneNumberField(
        verbose_name='телефон получателя *',
        help_text="Внесите телефон, прим. '+38212345678'. Для пустого значения, внесите 'None'.",
    )
    recipient_address = models.CharField(
        verbose_name='адрес доставки',
        max_length=100,
        blank=True, null=True
    )
    city = models.CharField(
        max_length=20,
        verbose_name="город *",
        choices=settings.CITY_CHOICES
    )
    time = models.DateTimeField(
        verbose_name='время доставки',
        blank=True, null=True,
    )
    comment = models.TextField(
        max_length=400,
        verbose_name='Комментарий',
        help_text='Комментарий к заказу.',
        blank=True, null=True
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.PROTECT,
        verbose_name='точка ',
        help_text="Подтянется автоматически.",
        related_name='заказы',

        blank=True,
        null=True,
    )
    persons_qty = models.PositiveSmallIntegerField(
        verbose_name='Кол-во приборов *',
        validators=[MaxValueValidator(10)]
    )
    amount = models.DecimalField(
        default=0.00,
        blank=True,
        max_digits=8, decimal_places=2,
        verbose_name='сумма заказа до скидки, DIN',
        help_text="Посчитается автоматически.",
    )
    promocode = models.ForeignKey(
        Promocode,
        verbose_name='Промокод',
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    discount = models.DecimalField(
        verbose_name='Доп скидка, DIN',
        help_text="Опциональная доп скидка вводится вручную в формате '0000.00'.",
        default=0.00,
        null=True,
        max_digits=8, decimal_places=2
    )
    discounted_amount = models.DecimalField(
        verbose_name='Сумма заказа после скидок, DIN',
        help_text="Посчитается автоматически.",
        default=0.00,
        blank=True,
        max_digits=8, decimal_places=2
    )
    final_amount_with_shipping = models.DecimalField(
        verbose_name='Сумма заказа с учетом скидок и доставки, DIN',
        help_text="Посчитается автоматически.",
        default=0.00,
        blank=True,
        max_digits=8, decimal_places=2
    )

    items_qty = models.PositiveSmallIntegerField(
        verbose_name='Кол-во ед-ц заказа, шт',
        help_text="Посчитается автоматически.",
        default=0,
        blank=True,
    )

    class Meta:
        ordering = ['-created']
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'
        constraints = [
            models.UniqueConstraint(
                fields=['order_number', 'created'],
                name='unique_order_number_created'
            )
        ]

    def __str__(self):
        return f'{self.id}'

    def calculate_discontinued_amount(self):
        """
        Рассчитывает final_amount с учетом спец скидок от промокода.
        """
        if self.promocode:
            # Если есть промокод, применяем скидку
            discount_amount = Decimal(self.amount) * Decimal(self.promocode.discount) / Decimal(100)
            self.discounted_amount = Decimal(self.amount) - discount_amount
        else:
            # Если нет промокода, final_amount равен общей сумме
            self.discounted_amount = Decimal(self.amount)
        if self.discount:
            # Если есть вручную внесенная скидка, применяем её
            self.discounted_amount = (
                Decimal(self.discounted_amount) - Decimal(self.discount)
            )

    def calculate_final_amount_with_shipping(self):
        """
        Рассчитывает final_amount с учетом скидки от промокода.
        """
        if self.delivery.type == 'delivery':
            self.delivery_cost = self.delivery.get_delivery_cost(
                self.city,
                self.discounted_amount,
                self.recipient_address
            )
            self.delivery_zone_db = self.delivery_zone.pk
        elif self.delivery.type == 'takeaway':
            if self.delivery.discount:
                takeaway_discount = (
                    Decimal(self.discounted_amount)
                    * Decimal(self.delivery.discount) / Decimal(100)
                )
                self.delivery_cost = (
                    Decimal(0 - takeaway_discount)
                )
            else:
                self.delivery_cost = Decimal(0)
        self.final_amount_with_shipping = (
            Decimal(self.discounted_amount) + Decimal(self.delivery_cost)
        )
        self.delivery_db = self.delivery.pk

    def clean(self):
        super().clean()
        # Проверяем, время доставки
        # from django.db.models.fields.related import ObjectDoesNotExist
        # try:
        #     delivery = self.cleaned_data.get('delivery')
        # except Exception as ex:
        #     raise ValidationError(f"{ex} Объект доставки не существует")
        # if delivery and self.time and self.restaurant:
        #     validate_order_time(self.time, self.delivery, self.restaurant)

    def save(self, *args, **kwargs):
        """
        Переопределяем метод save для автоматического рассчета final_amount перед сохранением.
        """
        self.full_clean()
        if self.pk is None:  # Если объект новый
            self.items_qty = 0
            self.order_number = self.get_next_item_id_today()

        else:
            # Если объект уже существует, выполнить рассчеты и другие действия
            self.get_restaurant(self.restaurant,
                                self.delivery.type,
                                self.recipient_address)

            self.calculate_discontinued_amount()
            self.calculate_final_amount_with_shipping()
            itemsqty = self.orderdishes.aggregate(qty=Sum('quantity'))
            self.items_qty = itemsqty['qty'] if itemsqty['qty'] is not None else 0

        super().save(*args, **kwargs)

    def get_restaurant(self, restaurant, delivery_type, recipient_address=None):
        if delivery_type == 'takeaway':
            self.restaurant = restaurant
        if delivery_type == 'delivery':
            self.restaurant = Restaurant.objects.get(id=1)

    def get_next_item_id_today(self):
        today_start = datetime.combine(date.today(), datetime.min.time())  # Начало текущего дня
        today_end = today_start + timedelta(days=1) - timedelta(microseconds=1)  # Конец текущего дня

        max_id = Order.objects.filter(
            created__range=(today_start, today_end)
        ).aggregate(Max('order_number'))['order_number__max']
        # Устанавливаем номер заказа на единицу больше MAX текущей даты
        if max_id is None:
            return 1
        else:
            return max_id + 1


class OrderDish(models.Model):
    """ Модель для сопоставления связи заказа и блюд."""
    dish = models.ForeignKey(
        Dish,
        on_delete=models.SET_NULL,
        related_name='orderdishes',
        verbose_name='Товары в заказе',
        null=True
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        verbose_name='Заказ',
        related_name='orderdishes',
        null=True
    )
    quantity = models.PositiveSmallIntegerField(
        verbose_name='Кол-во',
        validators=[MinValueValidator(1)],
    )
    unit_price = models.DecimalField(
        default=0.00,
        null=True,
        max_digits=6, decimal_places=2
    )
    amount = models.DecimalField(
        default=0.00,
        blank=True,
        max_digits=7, decimal_places=2
    )
    dish_article = models.PositiveSmallIntegerField(
        verbose_name='Запись блюда в БД',
        null=True, blank=True,
    )
    order_number = models.PositiveSmallIntegerField(
        verbose_name='Запись заказа в БД',
        null=True, blank=True,
    )
    base_profile = models.PositiveSmallIntegerField(
        verbose_name='Запись baseprofile в БД',
        null=True, blank=True,
    )

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

    def save(self, *args, **kwargs):
        self.amount = self.dish.final_price * self.quantity
        self.unit_price = self.dish.final_price
        self.dish_article = self.dish.pk
        self.order_number = self.order.pk

        super(OrderDish, self).save(*args, **kwargs)

        total_amount = OrderDish.objects.filter(
            order=self.order
                ).aggregate(ta=Sum('amount'))['ta']
        self.order.amount = total_amount if total_amount is not None else 0
        self.order.save(update_fields=[
            'amount',
            'discounted_amount',
            'final_amount_with_shipping',
            'delivery_cost',
            ])

    def delete(self, *args, **kwargs):
        super(OrderDish, self).delete()
        total_amount = OrderDish.objects.filter(
            order=self.order
                ).aggregate(ta=Sum('amount'))['ta']

        self.order.amount = total_amount if total_amount is not None else 0
        self.order.save(update_fields=[
            'amount',
            'discounted_amount',
            'final_amount_with_shipping',
            'delivery_cost',
            ])

    @staticmethod
    def create_orderdishes_from_cartdishes(order, cartdishes, base_profile):
        for cartdish in cartdishes:

            OrderDish.objects.create(
                order=order,
                dish=cartdish.dish,
                quantity=cartdish.quantity,
                base_profile=base_profile
            )

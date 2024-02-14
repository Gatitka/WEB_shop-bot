from decimal import Decimal

from django.conf import settings  # для импорта валюты
from django.contrib.auth import get_user_model
from django.core.validators import (MaxValueValidator, MinLengthValidator,
                                    MinValueValidator)
from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_save, pre_save  # signals
from django.dispatch import receiver  # signals
from phonenumber_field.modelfields import PhoneNumberField

from catalog.models import Dish
from delivery_contacts.models import Delivery, DeliveryZone, Restaurant
from promos.models import Promocode
from users.models import BaseProfile
from .validators import validate_delivery_time
from exceptions import NoDeliveryDataException
from django.core.exceptions import ValidationError


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


class ShoppingCart(models.Model):
    """ Модель для добавления блюд в корзину покупок."""
    user = models.OneToOneField(
        BaseProfile,
        on_delete=models.CASCADE,
        verbose_name='ID клиента',
        related_name='shopping_cart',
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
        default=0.00,
        blank=True,
        max_digits=10, decimal_places=2
    )

    items_qty = models.PositiveSmallIntegerField(
        verbose_name='Кол-во порций, шт',
        default=0,
        blank=True
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


class CartDish(models.Model):
    """ Модель для сопоставления связи корзины и блюд."""
    dish = models.ForeignKey(
        Dish,
        on_delete=models.CASCADE,
        related_name='cartdishes',
        verbose_name='Товары в корзине'
    )
    cart = models.ForeignKey(
        ShoppingCart,
        on_delete=models.CASCADE,
        verbose_name='Заказ',
        related_name='cartdishes',
    )
    quantity = models.PositiveSmallIntegerField(
        verbose_name='Кол-во',
        validators=[MinValueValidator(1)],
        default=1
    )
    unit_price = models.DecimalField(
        default=0.00,
        null=True, blank=True,
        max_digits=6, decimal_places=2
    )
    amount = models.DecimalField(
        default=0.00,
        blank=True,
        max_digits=7, decimal_places=2
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
        self.amount = self.dish.final_price * self.quantity
        self.unit_price = self.dish.final_price
        super(CartDish, self).save(*args, **kwargs)
        self.update_shopping_cart()

    def save_in_flow(self, *args, **kwargs):
        self.amount = Decimal(self.dish.final_price * self.quantity)
        self.unit_price = self.dish.final_price
        super(CartDish, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        super(CartDish, self).delete()
        total_amount = CartDish.objects.filter(cart=self.cart).aggregate(ta=Sum('amount'))['ta']
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
    user = models.ForeignKey(
        BaseProfile,
        on_delete=models.CASCADE,
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
        verbose_name='доставка'
    )
    delivery_zone = models.ForeignKey(
        DeliveryZone,
        on_delete=models.PROTECT,
        verbose_name='зона доставки',
        blank=True, null=True
    )
    delivery_cost = models.DecimalField(
        verbose_name='стоимость доставки',
        default=0.00,
        max_digits=7, decimal_places=2,
        blank=True, null=True,
    )
    # payment
    recipient_name = models.CharField(
        max_length=400,
        verbose_name='имя получателя'
    )
    recipient_phone = PhoneNumberField(
        verbose_name='телефон получателя',
        blank=True, null=True,
        help_text="Внесите телефон, прим. '+38212345678'. Для пустого значения, внесите 'None'.",
    )
    recipient_address = models.CharField(
        verbose_name='адрес доставки',
        max_length=200,
        blank=True, null=True
    )
    city = models.CharField(
        max_length=20,
        verbose_name="город",
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
        verbose_name='точка',
        related_name='заказы',
        blank=True,
        null=True,
        default=1
    )
    persons_qty = models.PositiveSmallIntegerField(
        verbose_name='Кол-во приборов',
        validators=[MaxValueValidator(10)]
    )
    amount = models.DecimalField(
        default=0.00,
        blank=True,
        max_digits=8, decimal_places=2,
        verbose_name='сумма заказа до скидки, DIN',
    )
    promocode = models.ForeignKey(
        Promocode,
        verbose_name='Промокод',
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    discount = models.DecimalField(
        verbose_name='Скидка, DIN',
        default=0.00,
        null=True,
        max_digits=8, decimal_places=2
    )
    discounted_amount = models.DecimalField(
        verbose_name='Сумма заказа после скидок, DIN',
        default=0.00,
        blank=True,
        max_digits=8, decimal_places=2
    )
    final_amount_with_shipping = models.DecimalField(
        verbose_name='Сумма заказа с учетом скидок и доставки, DIN',
        default=0.00,
        blank=True,
        max_digits=8, decimal_places=2
    )

    items_qty = models.PositiveSmallIntegerField(
        verbose_name='Кол-во ед-ц заказа, шт',
        default=0,
        blank=True,
    )

    class Meta:
        ordering = ['-created']
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'

    def __str__(self):
        return f'{self.id}'

    def calculate_discontinued_amount(self):
        """
        Рассчитывает final_amount с учетом скидки от промокода.
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
        elif self.delivery_id == 'takeaway':
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
        print(self.discounted_amount, self.delivery_cost)
        self.final_amount_with_shipping = (
            Decimal(self.discounted_amount) + Decimal(self.delivery_cost)
        )

    def clean(self):
        super().clean()
        # Проверяем, время доставки
        try:
            validate_delivery_time(self.time, self.delivery)
        except Exception as e:
            raise ValidationError(
                f'{e}'
            )

    def save(self, *args, **kwargs):
        """
        Переопределяем метод save для автоматического рассчета final_amount перед сохранением.
        """
        self.full_clean()
        if self.pk is None:  # Если объект новый
            self.items_qty = 0
        else:
            # Если объект уже существует, выполнить рассчеты и другие действия
            self.calculate_discontinued_amount()
            self.calculate_final_amount_with_shipping()
            itemsqty = self.order_dishes.aggregate(qty=Sum('quantity'))
            self.items_qty = itemsqty['qty'] if itemsqty['qty'] is not None else 0
        super().save(*args, **kwargs)


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
        on_delete=models.CASCADE,
        verbose_name='Заказ',
        related_name='order_dishes',
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


# ------    сигналы для создания cart при создании base_profile
@receiver(post_save, sender=BaseProfile)
def create_cart(sender, instance, created, **kwargs):
    if created:
        cart, created = ShoppingCart.objects.get_or_create(user=instance)

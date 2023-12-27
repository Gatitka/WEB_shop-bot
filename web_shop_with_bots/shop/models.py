from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MinLengthValidator, MaxValueValidator
from catalog.models import Dish
from users.models import BaseProfile
from django.db.models import Sum
from django.conf import settings # для импорта валюты
from delivery_contacts.models import Delivery, Shop
from promos.models import Promocode
from decimal import Decimal

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
    complited = models.BooleanField(
        verbose_name='Заказана',
        default=False
    )
    session_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    amount = models.DecimalField(
        verbose_name='Сумма, DIN',
        default=0.00,
        blank=True,
        max_digits=6, decimal_places=2
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
    final_amount = models.DecimalField(
        verbose_name='Итог сумма, DIN',
        default=0.00,
        blank=True,
        max_digits=6, decimal_places=2
    )

    @property
    def num_of_items(self):
        itemsqty = self.cart_dishes.aggregate(qty=Sum('quantity'))
        return itemsqty['qty']
    num_of_items.fget.short_description = 'Кол-во ед-ц тов, шт'

    class Meta:
        ordering = ['-created']
        verbose_name = 'корзина покупок'
        verbose_name_plural = 'корзины покупок'

    def __str__(self):
        return f'{self.user} -> корзина id={self.pk}'

    def calculate_final_amount(self):
        """
        Рассчитывает final_amount с учетом скидки от промокода.
        """
        print(self.cart_dishes)
        print(self.cart_dishes.all())
        if self.promocode:
            # Если есть промокод, применяем скидку
            discount_amount = self.amount * (self.promocode.discount / Decimal(100))
            self.final_amount = self.amount - discount_amount
        if self.discount:
            # Если есть вручную внесенная скидка, применяем её
            self.final_amount = self.amount - self.discount
        else:
            # Если нет промокода, final_amount равен общей сумме
            self.final_amount = self.amount

    def save(self, *args, **kwargs):
        """
        Переопределяем метод save для автоматического рассчета final_amount перед сохранением.
        """
        self.calculate_final_amount()
        super().save(*args, **kwargs)


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
        on_delete=models.CASCADE,
        verbose_name='Заказ',
        related_name='cart_dishes',
    )
    quantity = models.PositiveSmallIntegerField(
        verbose_name='Кол-во',
        validators=[MinValueValidator(1)],
        default=0
    )
    amount = models.DecimalField(
        default=0.00,
        blank=True,
        max_digits=6, decimal_places=2
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
        super(CartDish, self).save(*args, **kwargs)
        total_amount = CartDish.objects.filter(cart=self.cart).aggregate(ta=Sum('amount'))['ta']
        self.cart.amount = total_amount if total_amount is not None else 0
        self.cart.save(update_fields=['amount', 'final_amount'])

    def save_in_flow(self, *args, **kwargs):
        self.amount = self.dish.final_price * self.quantity
        super(CartDish, self).save(*args, **kwargs)


    def delete(self, *args, **kwargs):
        super(CartDish, self).delete()
        total_amount = CartDish.objects.filter(cart=self.cart).aggregate(ta=Sum('amount'))['ta']
        self.cart.amount = total_amount if total_amount is not None else 0
        self.cart.save(update_fields=['amount', 'final_amount'])


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
        Shop,
        on_delete=models.CASCADE,
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
        max_digits=6, decimal_places=2
    )

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
    unit_price = models.DecimalField(
        default=0.00,
        null=True,
        max_digits=6, decimal_places=2
    )
    amount = models.DecimalField(
        default=0.00,
        blank=True,
        max_digits=6, decimal_places=2
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
        super(OrderDish, self).save(*args, **kwargs)
        self.order.amount = OrderDish.objects.filter(order=self.order).aggregate(ta=Sum('amount'))['ta']
        self.order.save(update_fields=['amount'])

    def delete(self, *args, **kwargs):
        super(OrderDish, self).delete()
        self.order.amount = OrderDish.objects.filter(order=self.order).aggregate(ta=Sum('amount'))['ta']
        self.order.save(update_fields=['amount'])

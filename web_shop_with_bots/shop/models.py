from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model

from django.core.validators import (MaxValueValidator,
                                    MinValueValidator)
from django.db import models
from django.db.models import Sum
from phonenumber_field.modelfields import PhoneNumberField
from catalog.models import Dish
from delivery_contacts.models import Delivery, DeliveryZone, Restaurant
from delivery_contacts.utils import get_delivery_cost
from promos.models import Promocode
from promos.services import get_promocode_discount_amount
from shop.utils import get_first_item_true, get_next_item_id_today
from users.models import BaseProfile, UserAddress
from users.validators import validate_first_and_last_name
from django.utils.translation import gettext_lazy as _
# from shop.services import (get_amount, get_promocode_results,
#                            get_delivery_discount, check_total_discount,
#                            get_auth_first_order_discount)

User = get_user_model()

import logging

logger = logging.getLogger(__name__)


class ShoppingCart(models.Model):
    """ Модель для добавления блюд в корзину покупок."""
    user = models.ForeignKey(
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
        verbose_name='Сумма скидки по промокоду, DIN',
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
            self.discount, message, free_delivery = (
                        get_promocode_discount_amount(self.promocode,
                                                      amount=self.amount))

            # self.discount = (
            #     Decimal(self.amount) * Decimal(self.promocode.discount) / Decimal(100)
            # ).quantize(Decimal('0.01'))

            self.discounted_amount = (
                Decimal(self.amount) - self.discount
            ).quantize(Decimal('0.01'))
        else:
            # Если нет промокода и вручную внесенной скидки, final_amount равен общей сумме
            self.discounted_amount = self.amount
            self.discount = Decimal(0)

    def save(self, *args, **kwargs):
        """
        Переопределяем метод save для автоматического рассчета final_amount
        перед сохранением.
        """
        self.calculate_discounted_amount()
        if self.pk is None:  # Создание нового объекта
            self.items_qty = 0
        else:
            itemsqty = self.cartdishes.aggregate(qty=Sum('quantity'))
            self.items_qty = (itemsqty['qty'] if itemsqty['qty'] is not None
                              else 0)

        super().save(*args, **kwargs)

    def empty_cart(self):
        self.dishes.clear()  # Очищаем связанные товары
        self.amount = 0.00
        self.discount = 0.00
        self.discounted_amount = 0.00
        self.items_qty = 0
        self.promocode = None
        self.save()


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
        self.cart.save(update_fields=['amount', 'discounted_amount',
                                      'items_qty'])


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
        # default=timezone.now,
        auto_now_add=True
    )
    status = models.CharField(
        max_length=3,
        verbose_name="Статус",
        choices=settings.ORDER_STATUS_CHOICES,
        default="WCO"
    )
    city = models.CharField(
        max_length=20,
        verbose_name="город *",
        choices=settings.CITY_CHOICES,
        default=settings.DEFAULT_CITY
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

    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='доставка *',
        default=1
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
        default=0,
        max_digits=7, decimal_places=2,
        blank=True, null=True,
    )
    address_comment = models.CharField(
        verbose_name='Данные адреса',
        blank=True, null=True,
        max_length=50,
        default='flat: , floor: , interfon: ',
        help_text='flat: , floor: , interfon: '
        )
    coordinates = models.CharField(
        verbose_name='координаты',
        blank=True, null=True,
        max_length=50,
        )
    my_delivery_address = models.ForeignKey(
        UserAddress,
        on_delete=models.SET_NULL,
        verbose_name='Адрес из моих адресов',
        blank=True, null=True,
        )
    delivery_time = models.DateTimeField(
        verbose_name='время доставки',
        blank=True, null=True,
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.PROTECT,
        verbose_name='точка ',
        help_text="Подтянется автоматически.",
        related_name='заказы',
        blank=True,
        null=True,
        default=settings.DEFAULT_RESTAURANT
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
    promocode_disc_amount = models.DecimalField(
        verbose_name='скидка по промокоду, DIN',
        help_text="рассчитывается автоматически.",
        default=0,
        null=True,
        max_digits=8, decimal_places=2
    )
    auth_fst_ord_disc_amount = models.DecimalField(
        verbose_name='скидка за первый заказ, DIN',
        help_text="рассчитывается автоматически.",
        default=0,
        null=True,
        max_digits=8, decimal_places=2
    )
    takeaway_disc_amount = models.DecimalField(
        verbose_name='скидка самовывоз, DIN',
        help_text="рассчитывается автоматически.",
        default=0,
        null=True,
        max_digits=8, decimal_places=2
    )
    cash_discount_amount = models.DecimalField(
        verbose_name='скидка за оплату наличными, DIN',
        help_text="рассчитывается автоматически.",
        default=0,
        null=True,
        max_digits=8, decimal_places=2
    )
    manual_discount = models.DecimalField(
        verbose_name='Доп скидка, DIN',
        help_text="Опциональная доп скидка вводится вручную в формате '0000.00'.",
        default=0,
        null=True,
        max_digits=8, decimal_places=2
    )

    discounted_amount = models.DecimalField(
        verbose_name='Сумма заказа после скидок, DIN',
        help_text="Посчитается автоматически.",
        default=0,
        blank=True,
        max_digits=8, decimal_places=2
    )
    final_amount_with_shipping = models.DecimalField(
        verbose_name='Сумма заказа с учетом скидок и доставки, DIN',
        help_text="Посчитается автоматически.",
        default=0,
        blank=True,
        max_digits=8, decimal_places=2
    )
    payment_type = models.CharField(
        max_length=20,
        verbose_name="способ оплаты *",
        choices=settings.PAYMENT_METHODS,
        default='card_on_delivery'
    )

    dishes = models.ManyToManyField(
        Dish,
        through='OrderDish',
        # related_name='dish',
        verbose_name='Товары в заказе',
        help_text='Добавьте блюда в заказ.'
    )
    items_qty = models.PositiveSmallIntegerField(
        verbose_name='Кол-во ед-ц заказа, шт',
        help_text="Посчитается автоматически.",
        default=0,
        blank=True,
    )

    language = models.CharField(
        'lg',
        max_length=10,
        choices=settings.LANGUAGES,
        help_text="Язык общения.",
        null=True, blank=True,
        default=settings.DEFAULT_CREATE_LANGUAGE
    )
    comment = models.TextField(
        max_length=400,
        verbose_name='Комментарий',
        help_text='Уточнение по адресу доставки: частный дом / этаж, квартира, домофон. Прочие комм к заказу',
        blank=True, null=True
    )

    is_first_order = models.BooleanField(
        verbose_name='Первый заказ',
        default=False
    )
    created_by = models.PositiveSmallIntegerField(
        'кем создан',
        choices=settings.CREATED_BY,
        help_text="Кем создан заказ (клиент / админ).",
        null=True, blank=True,
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
        created = self.created.strftime('%H:%M  %Y.%m.%d')
        if self.is_first_order:
            return f"Заказ №  {self.order_number}/{self.id} от {created} /       ПЕРВЫЙ ЗАКАЗ"
        return f"Заказ №  {self.order_number}/{self.id} от {created}"

    def calculate_discontinued_amount(self):
        """
        Рассчитывает final_amount с учетом спец скидок от промокода.
        """
        self.discounted_amount = Decimal(0)
        promocode_data, self.promocode_disc_amount, free_delivery = (
            get_promocode_results(self.amount, self.promocode)
        )

        self.takeaway_disc_amount = get_delivery_discount(self.delivery,
                                                          self.amount)

        self.auth_fst_ord_disc_amount, fo_status = (
                            get_auth_first_order_discount(
                                self.amount,
                                base_profile=self.user))

        self.manual_discount = (self.manual_discount if self.manual_discount
                                else Decimal(0))

        self.cash_discount_amount = cash_discount(self.amount,
                                                  self.payment_type,
                                                  self.language)

        total_discount_sum = Decimal(
                                self.promocode_disc_amount
                                + self.takeaway_disc_amount
                                + self.auth_fst_ord_disc_amount
                                + self.cash_discount_amount
                                + self.manual_discount
                             ).quantize(Decimal('0.01'))

        # если заказ создан пользоватлем, то проверяется МАКС скидка 25%
        # если изменение при сохранении админом, то проверки на макс НЕТ.
        if self.created_by == 1 and self.status == 'WCO':
            total_discount, disc_lim_message = (
                                check_total_discount(
                                    self.amount,
                                    total_discount_sum)
                                )
        else:
            total_discount, disc_lim_message = total_discount_sum, ''

        self.discounted_amount = Decimal(
                                    self.amount - total_discount
                                 ).quantize(Decimal('0.01'))

        return free_delivery, fo_status, disc_lim_message

    def calculate_final_amount_with_shipping(self, free_delivery=False):
        """
        Рассчитывает final_amount с учетом скидки от промокода.
        """
        if self.delivery.type == 'delivery':

            self.delivery_cost = (
                get_delivery_cost(
                    self.amount,
                    self.delivery,
                    self.delivery_zone,
                    self.delivery_cost,
                    free_delivery
                )
            )
            if self.delivery_zone:
                self.delivery_zone_db = self.delivery_zone.pk

        self.final_amount_with_shipping = (
            Decimal(self.discounted_amount) + Decimal(self.delivery_cost)
        ).quantize(Decimal('0.01'))

        self.delivery_db = self.delivery.pk

    def save(self, *args, **kwargs):
        """
        Переопределяем метод save для автоматического рассчета final_amount
        перед сохранением.
        """
        self.full_clean()

        # Если объект уже существует, выполнить рассчеты и другие действия
        self.get_restaurant(self.restaurant,
                            self.delivery.type,
                            self.recipient_address)

        if self.pk is None:  # Если объект новый

            self.order_number = get_next_item_id_today(Order, 'order_number')

            self.is_first_order = get_first_item_true(self)

            self.items_qty = 0

            self.language = (settings.DEDEFAULT_CREATE_LANGUAGE
                             if self.language is None else self.language)

            super(Order, self).save(*args, **kwargs)
            return

        free_delivery, fo_status, disc_lim_message = (
            self.calculate_discontinued_amount())

        self.calculate_final_amount_with_shipping(free_delivery)

        itemsqty = self.orderdishes.aggregate(qty=Sum('quantity'))
        self.items_qty = itemsqty['qty'] if itemsqty['qty'] is not None else 0

        super(Order, self).save(*args, **kwargs)
        # далее есть сигнал на сохранение актуальной корзины пользователя,
        # если есть, в completed

    def get_restaurant(self, restaurant, delivery_type,
                       recipient_address=None):
        """
        Метод получения ресторана, исходя из запроса.
        Если есть ресторан, с отметкой is_default,
        то все заказы переводятся на него.
        """
        default_restaurant = Restaurant.objects.filter(is_default=True).first()
        if default_restaurant:
            self.restaurant = default_restaurant
        else:
            if delivery_type == 'takeaway':
                self.restaurant = restaurant
            if delivery_type == 'delivery':
                self.restaurant = Restaurant.objects.get(id=1)


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
        on_delete=models.CASCADE,
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
    unit_amount = models.DecimalField(
        default=0.00,
        blank=True,
        max_digits=7, decimal_places=2
    )
    dish_article = models.PositiveSmallIntegerField(
        verbose_name='Арт. блюда/БД',
        null=True, blank=True,
    )
    order_number = models.PositiveSmallIntegerField(
        verbose_name='# заказа/БД',
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
        self.unit_amount = self.dish.final_price * self.quantity
        self.unit_price = self.dish.final_price
        self.dish_article = self.dish.pk
        self.order_number = self.order.pk

        super(OrderDish, self).save(*args, **kwargs)

        total_amount = OrderDish.objects.filter(
            order=self.order
                ).aggregate(ta=Sum('unit_amount'))['ta']
        self.order.amount = total_amount if total_amount is not None else 0
        self.order.save(update_fields=[
            'delivery_cost', 'items_qty',
            'amount',
            'promocode_disc_amount', 'auth_fst_ord_disc_amount',
            'takeaway_disc_amount', 'cash_discount_amount',
            'discounted_amount', 'final_amount_with_shipping',
            ])

    def delete(self, *args, **kwargs):
        super(OrderDish, self).delete()
        total_amount = OrderDish.objects.filter(
            order=self.order
                ).aggregate(ta=Sum('unit_amount'))['ta']

        self.order.amount = total_amount if total_amount is not None else 0
        self.order.save(update_fields=[
            'amount',
            'discounted_amount',
            'final_amount_with_shipping',
            'delivery_cost',
            'items_qty',
            ])

    @staticmethod
    def create_orderdishes_from_cartdishes(order,
                                           cartdishes=None,
                                           no_cart_cartdishes=None):
        if cartdishes:
            for cartdish in cartdishes:

                OrderDish.objects.create(
                    order=order,
                    dish=cartdish.dish,
                    quantity=cartdish.quantity
                )

        elif no_cart_cartdishes:
            for cartdish in no_cart_cartdishes:

                OrderDish.objects.create(
                    order=order,
                    dish=cartdish['dish'],
                    quantity=cartdish['quantity']
                )


class Discount(models.Model):
    """ Модель для скидок."""
    type = models.CharField(
        max_length=20,
        verbose_name="тип скидки",
        unique=True,
        choices=settings.DISCOUNT_TYPES
    )
    discount_perc = models.DecimalField(
        verbose_name='Скидка в %',
        help_text="Внесите скидку, прим. для 10% внесите '10,00'.",
        max_digits=7, decimal_places=2,
        null=True,
        blank=True,
    )
    discount_am = models.DecimalField(
        verbose_name='Скидка в RSD',
        help_text="Внесите скидку, прим. '300,00'.",
        max_digits=7, decimal_places=2,
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name='Активен'
    )
    created = models.DateField(
        'Дата добавления', auto_now_add=True
    )
    valid_from = models.DateTimeField(
        'Начало действия'
    )
    valid_to = models.DateTimeField(
        'Окончание действия'
    )

    title_rus = models.CharField(
        max_length=100,
        verbose_name='описание'
    )

    class Meta:
        ordering = ['id']
        verbose_name = _("discount")
        verbose_name_plural = _("discounts")
        constraints = [
            models.UniqueConstraint(
                fields=['type', 'title_rus'],
                name='unique_type_title_rus'
            )
        ]

    def __str__(self):
        return self.title_rus

    def show_discount(self):
        if self.discount_perc:
            return f"{self.discount_perc} %"

        if self.discount_am:
            return f"{self.discount_am} %"

    def calculate_discount(self, amount):
        if self.discount_perc:
            return (
                Decimal(amount) * Decimal(self.discount_perc)
                / Decimal(100)).quantize(Decimal('0.01'))

        if self.discount_am:
            return self.discount_am


def get_amount(cart=None, items=None):
    if cart:
        return cart.amount

    if items:
        amount = Decimal(0)
        for item in items:
            dish = item['dish']
            amount += Decimal(dish.final_price * item['quantity'])
        return amount


def get_promocode_results(amount, promocode=None,
                          request=None, cart=None):
    # if cart:
    #     if cart.promocode is None:
    #         promocode_code = None
    #         promocode_discount = Decimal(0)
    #         discounted_amount = amount
    #         free_delivery = False

    #     else:
    #         promocode_code = cart.promocode.code
    #         promocode_discount = cart.discount
    #         discounted_amount = cart.discounted_amount
    #         free_delivery = cart.promocode.free_delivery

    #     message = ''
    #     return (promocode_code, promocode_discount,
    #             discounted_amount, message, free_delivery)

    # else:
    #  для незареганых пользователей
    if promocode is None:
        promocode_data = {
            "promocode": None,
            "valid": "invalid",
            "detail": ""}
        promocode_discount = Decimal(0)
        free_delivery = False

    else:
        promocode_discount, message, free_delivery = (
            get_promocode_discount_amount(
                promocode, amount, request,
            ))
        promocode_data = {
            "promocode": promocode.code,
            "valid": "valid",
            "detail": message}

    return promocode_data, promocode_discount, free_delivery


def get_auth_first_order_discount(amount, base_profile=None,
                                  web_account=None):
    if base_profile:
        if base_profile.orders_qty == 0:
            fo_discount, fo_status = auth_first_order_discount(amount)
            return fo_discount, fo_status

    elif web_account:
        if web_account.is_authenticated:
            if web_account.base_profile.orders_qty == 0:
                fo_discount, fo_status = auth_first_order_discount(amount)
                return fo_discount, fo_status

    return Decimal(0), False


def auth_first_order_discount(amount):
    fst_ord_disc = Discount.objects.filter(type="1", is_active=True).first()
    if fst_ord_disc:
        fo_dis_amount = fst_ord_disc.calculate_discount(amount)
        return fo_dis_amount, True
    return Decimal(0), False


def get_delivery_discount(delivery, discounted_amount):
    if delivery.discount:
        delivery_discount = (
            Decimal(discounted_amount)
            * Decimal(delivery.discount) / Decimal(100)
        ).quantize(Decimal('0.01'))
    else:
        delivery_discount = Decimal(0)
    return delivery_discount


def cash_discount(amount, payment_type, language):
    if payment_type == 'cash' and language == 'ru':
        cash_discount = Discount.objects.filter(type="2",
                                                is_active=True).first()
        if cash_discount:
            cash_disc_amnt = cash_discount.calculate_discount(amount)
            return cash_disc_amnt
    return Decimal(0)


def check_total_discount(amount, total_discount_sum):
    max_disc_amount = (
        amount * Decimal(settings.MAX_DISC_AMOUNT) / Decimal(100)
        ).quantize(Decimal('0.01'))

    if total_discount_sum <= max_disc_amount:
        message = ""
        return total_discount_sum, message

    message = _("The total order discount cannot exceed 25%.")
    return max_disc_amount, message

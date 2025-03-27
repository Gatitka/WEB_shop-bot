from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model

from django.core.validators import (MaxValueValidator,
                                    MinValueValidator)
from django.db import models
from django.db.models import Sum, F
from phonenumber_field.modelfields import PhoneNumberField
from catalog.models import Dish
from delivery_contacts.models import (Delivery, DeliveryZone,
                                      Restaurant, Courier)
from delivery_contacts.utils import get_delivery_cost
from promos.models import Promocode
from promos.services import get_promocode_discount_amount
from shop.utils import get_first_order_true, get_next_item_id_today
from users.models import BaseProfile, UserAddress
from users.validators import validate_first_and_last_name
from django.utils.translation import gettext_lazy as _
from tm_bot.models import MessengerAccount, OrdersBot
from django.utils import timezone
from django.db.models import Max
from django.urls import reverse


User = get_user_model()

import logging

logger = logging.getLogger(__name__)


class Order(models.Model):
    """ Модель для заказов."""
    objects = models.Manager()
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
        max_length=200,
        blank=True, null=True
    )
    created = models.DateTimeField(
        'Дата создания',
        auto_now_add=True
        # default=timezone.now,
        # editable=True  # Explicitly make it editable
    )
    # execution_date = models.DateField(
    #     'Дата выполнения',
    #     null=True,
    #     blank=True
    # )
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
        verbose_name='имя получателя',
        # validators=[validate_first_and_last_name,], из-за бота
        blank=True, null=True
    )
    recipient_phone = models.CharField(
        verbose_name='телефон получателя',
        max_length=128,
        help_text="Внесите телефон, прим. '+38212345678'.",
        blank=True, null=True
    )
    recipient_address = models.CharField(
        verbose_name='адрес доставки',
        max_length=400,
        blank=True, null=True,
    )

    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='доставка',
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
        default=0,
        max_digits=7, decimal_places=2,
        blank=True, null=True,
    )
    address_comment = models.CharField(
        verbose_name='Данные адреса',
        blank=True, null=True,
        max_length=400,
        default='flat: , floor: , interfon: ',
        help_text='flat: #####, floor: #####, interfon: ##########'
        )
    coordinates = models.CharField(
        verbose_name='координаты',
        blank=True, null=True,
        max_length=100,
        )
    my_delivery_address = models.ForeignKey(
        UserAddress,
        on_delete=models.SET_NULL,
        verbose_name='Адрес из моих адресов',
        blank=True, null=True,
        )
    delivery_time = models.DateTimeField(
        verbose_name='время выдачи',
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
        validators=[MaxValueValidator(50)],
        null=True, blank=True
    )

    amount = models.DecimalField(
        default=0.00,
        blank=True,
        max_digits=8, decimal_places=2,
        verbose_name='сумма заказа до скидки, DIN',
        help_text="Посчитается автоматически.",
    )
    amount_with_shipping = models.DecimalField(
        verbose_name='Сумма заказа с учетом доставки, DIN',
        help_text="Посчитается автоматически.",
        default=0,
        blank=True,
        max_digits=8, decimal_places=2
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
        blank=True,
        max_digits=8, decimal_places=2
    )
    discount = models.ForeignKey(
        'Discount',
        verbose_name='скидка',
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    discount_amount = models.DecimalField(
        verbose_name='размер скидки, DIN',
        help_text="рассчитывается автоматически.",
        default=0, null=True,
        blank=True,
        max_digits=8, decimal_places=2
    )
    # auth_fst_ord_disc = models.BooleanField(
    #     verbose_name='скидка за первый заказ',
    #     default=False
    # )
    # auth_fst_ord_disc_amount = models.DecimalField(
    #     verbose_name='скидка за первый заказ, DIN',
    #     help_text="рассчитывается автоматически.",
    #     default=0,
    #     null=True,
    #     max_digits=8, decimal_places=2
    # )
    # takeaway_disc = models.BooleanField(
    #     verbose_name='скидка самовывоз',
    #     default=False
    # )
    # takeaway_disc_amount = models.DecimalField(
    #     verbose_name='скидка самовывоз, DIN',
    #     help_text="рассчитывается автоматически.",
    #     default=0,
    #     null=True,
    #     max_digits=8, decimal_places=2
    # )
    # cash_discount_disc = models.BooleanField(
    #     verbose_name='скидка за оплату наличными',
    #     default=False
    # )
    # cash_discount_amount = models.DecimalField(
    #     verbose_name='скидка за оплату наличными, DIN',
    #     help_text="рассчитывается автоматически.",
    #     default=0,
    #     null=True,
    #     max_digits=8, decimal_places=2
    # )
    manual_discount = models.DecimalField(
        verbose_name='Доп скидка, %',
        help_text="Доп скидка вводится вручную прим.'10.00'.<br>",
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
        null=True, blank=True
    )
    is_paid = models.BooleanField(
        verbose_name='оплачен',
        default=False
    )
    invoice = models.BooleanField(
        verbose_name='чек',
        default=True
    )
    source = models.CharField(
        max_length=20,
        verbose_name="источник заказа *",
        choices=settings.SOURCE_TYPES,
        default='4'
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
        max_length=1500,
        verbose_name='Комментарий',
        help_text=(
            'Уточнение по адресу доставки: частный дом / '
            'этаж, квартира, домофон. Прочие комм к заказу'),
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
    source_id = models.CharField(
        'ID источника',
        max_length=20,
        help_text="ID заказа в системе-источнике<br>(TmBot/Wolt/Glovo/Smoke/NeTa/SealTea).",
        null=True, blank=True,
    )
    msngr_account = models.ForeignKey(
        MessengerAccount,
        on_delete=models.SET_NULL,
        verbose_name='Аккаунт в соц сетях',
        related_name='orders',
        blank=True, null=True
    )
    courier = models.ForeignKey(
        Courier,
        on_delete=models.PROTECT,
        verbose_name='Курьер',
        related_name='orders',
        blank=True, null=True
    )
    process_comment = models.TextField(
        'ошибки сохранения',
        max_length=1500,
        null=True, blank=True,
    )
    admin_tm_msg_id = models.CharField(
        verbose_name='Номер сообщения в админском чате',
        max_length=500,
        blank=True, null=True
    )
    orders_bot = models.ForeignKey(
        OrdersBot,
        on_delete=models.PROTECT,
        verbose_name='Бот д/заказов',
        related_name='orders',
        blank=True, null=True
    )

    class Meta:
        ordering = ['-created']
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'
        constraints = [
            models.UniqueConstraint(
                fields=['order_number', 'created'],
                name='unique_order_number_created'
            ),
        ]

        permissions = [("can_create_order_rest_1", "Can create order rest 1"),
                       ("can_change_order_rest_1", "Can change order rest 1"),
                       ("can_delete_order_rest_1", "Can delete order rest 1"),
                       ("can_create_order_rest_2", "Can create order rest 2"),
                       ("can_change_order_rest_2", "Can change order rest 2"),
                       ("can_delete_order_rest_2", "Can delete order rest 2")
                       ]

    def __str__(self):
        created = self.created.strftime('%H:%M  %Y.%m.%d')
        order_info = f"Заказ №  {self.order_number}/{self.id} от {created}, {self.city}, {self.restaurant}"
        if self.is_first_order:
            return order_info + " /       ПЕРВЫЙ ЗАКАЗ"
        return order_info

    def select_promocode_vs_discount(self, promocode_disc_am,
                                     max_discount, max_discount_amount):
        result = promocode_vs_discount(promocode_disc_am,
                                       max_discount_amount)
        if result == {'promo': False, 'max_disc': True}:
            # self.validated_data['promocode'] = None     оставить для статистики
            self.promocode_disc_amount = Decimal(0)
            self.discount = max_discount
            self.discount_amount = max_discount_amount
            self.total_discount_amount = max_discount_amount

        elif result == {'promo': True, 'max_disc': False}:
            self.promocode_disc_amount = promocode_disc_am
            self.discount = None
            self.discount_amount = Decimal(0)
            self.total_discount_amount = promocode_disc_am

    def calculate_discontinued_amount(self, is_admin_mode=False):
        """
        Рассчитывает final_amount с учетом спец скидок от промокода.
        """
        self.discounted_amount = Decimal(0)

        promocode_data, self.promocode_disc_amount, free_delivery = (
            get_promocode_results(self.amount_with_shipping, self.promocode)
        )

        if self.source in settings.PARTNERS_LIST:
            self.discounted_amount = self.amount
            self.amount_with_shipping = self.amount
            return False, False

        max_discount, max_discount_amount, fo_status = (
            get_discount(self.user,
                         self.payment_type,
                         self.delivery,
                         self.source,
                         self.amount_with_shipping,
                         self.language,
                         self.discount,
                         self.is_first_order,
                         is_admin_mode))

        self.select_promocode_vs_discount(self.promocode_disc_amount,
                                          max_discount, max_discount_amount)

        if self.manual_discount:
            # если задана ручная скидка, то это скорее всего админ сохраняет
            # и обычная скидка стирается, а ручная скидка становится основной
            if self.manual_discount > 0:
                self.discount_amount = Decimal(
                                        self.amount_with_shipping
                                        * self.manual_discount / 100
                                    ).quantize(Decimal('0.01'))
                self.discount = None
                self.total_discount_amount = self.discount_amount

        self.discounted_amount = Decimal(
                                    self.amount_with_shipping
                                    - self.total_discount_amount
                                ).quantize(Decimal('0.01'))

        return free_delivery, fo_status

    def calculate_amount_with_shipping(self, free_delivery=False):
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

        self.amount_with_shipping = (
            Decimal(self.amount) + Decimal(self.delivery_cost)
        ).quantize(Decimal('0.01'))

        self.delivery_db = self.delivery.pk

    def save(self, *args, **kwargs):
        """
        Переопределяем метод save для автоматического рассчета final_amount
        перед сохранением.
        """
        self.full_clean()

        self.get_restaurant(self.city,
                            self.restaurant,
                            self.delivery.type,
                            self.recipient_address)

        is_admin_mode = kwargs.pop('is_admin_mode', False)

        if self.pk is None:  # Если объект новый

            self.order_number = get_next_item_id_today(Order, 'order_number',
                                                       self.restaurant)

            self.is_first_order = get_first_order_true(self)

            self.items_qty = 0

            self.language = (settings.DEDEFAULT_CREATE_LANGUAGE
                             if self.language is None else self.language)

            super(Order, self).save(*args, **kwargs)
            return

        # Если объект уже существует, выполнить рассчеты и другие действия
        self.calculate_amount_with_shipping()

        free_delivery, fo_status = (
            self.calculate_discontinued_amount(is_admin_mode))

        self.final_amount_with_shipping = self.discounted_amount

        itemsqty = self.orderdishes.aggregate(qty=Sum('quantity'))
        self.items_qty = itemsqty['qty'] if itemsqty['qty'] is not None else 0
        if self.persons_qty != self.items_qty:
            self.persons_qty = self.items_qty

        super(Order, self).save(*args, **kwargs)
        # далее есть сигнал на сохранение актуальной корзины пользователя,
        # если есть, в completed

    def get_restaurant(self, city, restaurant, delivery_type,
                       recipient_address=None):
        """
        Метод получения ресторана, исходя из запроса.
        Если есть в городе ресторан, с отметкой is_default,
        то все заказы переводятся на него.
        """
        default_restaurant = Restaurant.objects.filter(
            city=city,
            is_default=True).first()
        if default_restaurant:
            self.restaurant = default_restaurant
        else:
            if delivery_type == 'takeaway':
                self.restaurant = restaurant
            if delivery_type == 'delivery':
                self.restaurant = restaurant

    def get_admin_url(self):
        if self.source == 'P1-1':
            return reverse('admin:shop_orderglovoproxy_change', args=[self.pk])
        elif self.source == 'P1-2':
            return reverse('admin:shop_orderwoltproxy_change', args=[self.pk])
        elif self.source == 'P2-1':
            return reverse('admin:shop_ordersmokeproxy_change', args=[self.pk])
        elif self.source == 'P2-2':
            return reverse('admin:shop_ordernetadverproxy_change', args=[self.pk])
        return reverse('admin:shop_order_change', args=[self.pk])

    def transit_all_msngr_orders_to_base_profile(self, user):
        msngr_account = self.msngr_account
        updated_orders_count = Order.objects.filter(
            msngr_account=msngr_account,
            source='3',
            user=None
        ).update(user=user)

        # Обновляем количество заказов у пользователя
        user.orders_qty = F('orders_qty') + updated_orders_count
        user.save(update_fields=['orders_qty'])

    def get_city_short(self):
        if self.city == 'Beograd':
            return 'БГ'
        elif self.city == 'NoviSad':
            return 'НС'

    def get_source_display(self):
        SOURCE_DICT = dict(settings.SOURCE_TYPES)
        return SOURCE_DICT[self.source]


class OrderWoltProxy(Order):
    objects = models.Manager()

    class Meta:
        proxy = True
        verbose_name = 'заказ Wolt'
        verbose_name_plural = 'заказы Wolt'


class OrderGlovoProxy(Order):
    objects = models.Manager()

    class Meta:
        proxy = True
        verbose_name = 'заказ Glovo'
        verbose_name_plural = 'заказы Glovo'


class OrderSmokeProxy(Order):
    objects = models.Manager()

    class Meta:
        proxy = True
        verbose_name = 'заказ Smoke'
        verbose_name_plural = 'заказы Smoke'


class OrderNeTaDverProxy(Order):
    objects = models.Manager()

    class Meta:
        proxy = True
        verbose_name = 'заказ Не та дверь'
        verbose_name_plural = 'заказы Не та дверь'


class OrderSealTeaProxy(Order):
    objects = models.Manager()

    class Meta:
        proxy = True
        verbose_name = 'заказ Seal Tea'
        verbose_name_plural = 'заказы Seal Tea'


class OrderDish(models.Model):
    """ Модель для сопоставления связи заказа и блюд."""
    dish = models.ForeignKey(
        Dish,
        on_delete=models.SET_NULL,
        related_name='orderdishes',
        verbose_name='Товары в заказе',
        null=True,
        help_text=(
            'Перед удалением поставьте кол-во 0 для обнуления ИТОГО.'),
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
        default=1,
        validators=[MinValueValidator(1)],
        help_text=(
            'Перед удалением поставьте кол-во 0 для обнуления ИТОГО.'),
    )
    unit_price = models.DecimalField(
        default=0.00,
        null=True,
        max_digits=9, decimal_places=2
    )
    unit_amount = models.DecimalField(
        default=0.00,
        blank=True,
        max_digits=8, decimal_places=2
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
        self.dish_article = self.dish.pk
        self.order_number = self.order.pk
        if self.order.source in ['P1-1', 'P1-2']:
            self.unit_amount = self.dish.final_price_p1 * self.quantity
            self.unit_price = self.dish.final_price_p1
        elif self.order.source in ['P2-1', 'P2-2']:
            self.unit_amount = self.dish.final_price_p2 * self.quantity
            self.unit_price = self.dish.final_price_p2
        else:
            self.unit_amount = self.dish.final_price * self.quantity
            self.unit_price = self.dish.final_price

        super(OrderDish, self).save(*args, **kwargs)

        total_amount = OrderDish.objects.filter(
            order=self.order
                ).aggregate(ta=Sum('unit_amount'))['ta']
        self.order.amount = total_amount if total_amount is not None else 0
        self.order.save(update_fields=[
            'delivery_cost', 'items_qty', 'persons_qty',
            'amount', 'amount_with_shipping',
            'promocode_disc_amount', 'discount_amount',
            'discount', 'discount_amount',
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
    type = models.IntegerField(
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
            return f"{int(self.discount_perc)}%"

        if self.discount_am:
            return f"{int(self.discount_am)} RSD"

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
        promocode_disc_am = Decimal(0)
        free_delivery = False

    else:
        promocode_disc_am, message, free_delivery = (
            get_promocode_discount_amount(
                promocode, amount, request,
            ))
        promocode_data = {
            "promocode": promocode.code,
            "valid": "valid",
            "detail": message}

    return promocode_data, promocode_disc_am, free_delivery

# ???
def get_auth_first_order_discount(amount, base_profile=None,
                                  web_account=None):
    if base_profile:
        if base_profile.orders_qty == 0:
            fo_discount, fo_status, discount = auth_first_order_discount(amount)
            return fo_discount, fo_status, discount

    elif web_account:
        if web_account.is_authenticated:
            if web_account.base_profile.orders_qty == 0:
                fo_discount, fo_status = auth_first_order_discount(amount)
                return fo_discount, fo_status

    return Decimal(0), False

# ???
def auth_first_order_discount(amount):
    fst_ord_disc = Discount.objects.filter(type="1", is_active=True).first()
    if fst_ord_disc:
        fo_dis_amount = fst_ord_disc.calculate_discount(amount)
        return fo_dis_amount, True, {fst_ord_disc: fo_dis_amount}
    return Decimal(0), False, {None, Decimal(0)}


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


def current_cash_disc_status():
    cash_on_delivery_disc = Discount.objects.filter(
        type='3', is_active=True).first()
    if cash_on_delivery_disc:
        return cash_on_delivery_disc.show_discount()
    return None


def get_discount(user, payment, delivery, source, amount, language, discount,
                 is_first_order=False, is_admin_mode=False):

    order_details = get_order_details(user, payment, delivery,
                                      source, language, is_first_order)

    if is_admin_mode is False:
        #    and (discount is None or discount.type not in [4, 5, 6])):
        # при автоматическом сохранении заказа из сайта, необходимо выбрать
        # из подходящих скидок ту, что с большим %.
        # Прим. 1й заказ 5% (type 1) и самовывоз 10% (type 2) - нужно выбрать 10%
        # Была еще скидка type 3 за оплату кэшом, отменена, поэтому 1 / 2 / 3 перепроверяются
        # во всех остальных случаях скидка остается той же, что и задана
        order_details['amount'] = amount
        discounts = Discount.objects.filter(is_active=True)
        max_discount, max_discount_am = select_discount_api(discounts,
                                                            order_details)
    elif is_admin_mode is True:
        # сохраняем ту скидку, что указана без перевыбора
        max_discount = discount
        if discount is not None:
            max_discount_am = discount.calculate_discount(amount)
        else:
            max_discount_am = Decimal(0)
    return max_discount, max_discount_am, order_details['auth_first_order']


def get_order_details(user,
                      payment, delivery, source, language, is_first_order):
    order_details = {}
    if is_first_order in [False, None]:
        order_details['auth_first_order'] = check_auth_first_order(
                            base_profile=user)
    else:
        order_details['auth_first_order'] = True
    order_details['takeaway'] = check_takeaway(source, delivery)
    order_details['cash_payment'] = check_payment(source, delivery, payment,
                                                  language)
    return order_details


def check_auth_first_order(base_profile=None,
                           web_account=None):
    if base_profile:
        if base_profile.first_web_order is False:
            return True

    elif web_account:
        if web_account.is_authenticated:
            if web_account.base_profile.orders_qty is False:
                return True

    return False


def check_takeaway(source, delivery):
    if source in ['1', '2', '3', '4']:
        if delivery.type == 'takeaway' and delivery.discount:
            return True
    return False


def check_payment(source, delivery, payment, language):
    if (source in ['1', '2', '3', '4']
        and delivery.type == 'delivery'
            and payment == 'cash'
            and language == 'ru'):
        return True
    return False


def select_discount_api(discounts, order_details):
    max_discount = [None, Decimal(0)]
    amount = order_details['amount']
    for discount in discounts:
        discount_am = Decimal(0)

        if discount.type == 1 and order_details['auth_first_order']:
            discount_am = discount.calculate_discount(amount)

        elif discount.type == 2 and order_details['takeaway']:
            discount_am = discount.calculate_discount(amount)

        elif discount.type == 3 and order_details['cash_payment']:
            discount_am = discount.calculate_discount(amount)

        if discount_am and discount_am > max_discount[1]:
            max_discount = [discount, discount_am]

    return max_discount[0], max_discount[1]


def promocode_vs_discount(promocode_disc_am, max_disc_am):
    if promocode_disc_am >= max_disc_am:
        return {'promo': True, 'max_disc': False}
    else:
        return {'promo': False, 'max_disc': True}


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

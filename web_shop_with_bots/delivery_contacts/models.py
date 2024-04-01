from collections.abc import Iterable
from datetime import time
from decimal import Decimal

import requests
from django.conf import settings  # для импорта городов
from django.contrib.gis.db.models import MultiPolygonField, PointField
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.safestring import mark_safe
from parler.models import TranslatableModel, TranslatedFields
from phonenumber_field.modelfields import PhoneNumberField

from web_shop_with_bots.settings import GOOGLE_API_KEY

from .utils import google_validate_address_and_get_coordinates

DELIVERY_CHOICES = (
    ("delivery", "Доставка"),
    ("takeaway", "Самовывоз")
)


class Delivery(TranslatableModel):
    translations = TranslatedFields(
        description=models.TextField(
            max_length=400,
            verbose_name='Описание',
            null=True,
            blank=True
        ),
    )
    city = models.CharField(
        max_length=20,
        verbose_name="Город *",
        choices=settings.CITY_CHOICES
    )
    type = models.CharField(
        max_length=8,
        verbose_name="Тип *",
        choices=DELIVERY_CHOICES
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name='Активен *'
    )
    min_order_amount = models.DecimalField(
        verbose_name='MIN сумма заказа, DIN',
        validators=[MinValueValidator(0.01)],
        max_digits=7, decimal_places=2,
        help_text='Внесите цену в DIN. Формат 00000.00',
        null=True,
        blank=True
    )
    default_delivery_cost = models.DecimalField(
        verbose_name='Стоимость доставки по-умолчанию, DIN',
        validators=[MinValueValidator(0.01)],
        help_text='Внесите цену в DIN. Формат 00000.00',
        max_digits=7, decimal_places=2,
        null=True,
        blank=True
    )
    min_time = models.TimeField(
        verbose_name='MIN время заказа',
        default=time(10, 30),
        null=True,
        blank=True
        )
    max_time = models.TimeField(
        verbose_name='MAX время заказа',
        default=time(21, 30),
        null=True,
        blank=True
        )
    discount = models.DecimalField(
        verbose_name='Скидка на самовывоз, %',
        help_text="Внесите скидку, прим. для 10% внесите '10,00'.",
        max_digits=7, decimal_places=2,
        null=True,
        blank=True,
    )
    image = models.ImageField(
        upload_to='contacts/',
        null=True,
        default=None,
        blank=True,
        verbose_name='Карта районов доставки',
    )

    def admin_photo(self):
        if self.image:
            return mark_safe(
                '<img src="{}" width="100" />'.format(self.image.url)
                )
        missing_image_url = "icons/missing_image.jpg"
        return mark_safe(
            '<img src="{}" width="100" />'.format(missing_image_url)
            )

    admin_photo.short_description = 'Image'
    admin_photo.allow_tags = True

    @staticmethod
    def get_delivery_conditions(type):
        if type == 'takeaway':
            queryset = Delivery.objects.filter(
                    is_active=True,
                    type=type
                ).all().values(
                    'city', 'min_time', 'max_time',
                    'discount'
                )
        if type == 'delivery':
            queryset = Delivery.objects.filter(
                    is_active=True,
                    type=type
                ).all().values(
                    'city', 'min_time', 'max_time',
                    'min_order_amount',
                )
        return queryset

    class Meta:
        verbose_name = 'доставка'
        verbose_name_plural = 'способы доставки'

    def __str__(self):
        return f'{self.type}'


class DeliveryZone(models.Model):
    """ Модель для стоимости доставки по районам."""
    city = models.CharField(
        max_length=20,
        verbose_name="город",
        choices=settings.CITY_CHOICES
    )
    name = models.CharField(
            max_length=200,
            db_index=True,
            verbose_name='Название'
    )
    polygon = MultiPolygonField(
         null=True, blank=True
    )

    is_promo = models.BooleanField(
        verbose_name='PROMO',
        default=False
    )
    promo_min_order_amount = models.DecimalField(
        verbose_name='PROMO мин сумма заказа, DIN',
        max_digits=10, decimal_places=2,
        null=True, blank=True,
    )
    delivery_cost = models.DecimalField(
        verbose_name='стоимость доставки, DIN',
        default=0.00,
        blank=True,
        max_digits=10, decimal_places=2
    )

    def is_point_inside(self, lat, lon):
        point = Point(lon, lat)  # Создаем объект точки
        return self.polygon.contains(point)

    class Meta:
        verbose_name = 'район доставки'
        verbose_name_plural = 'районы доставки'

    def __str__(self):
        return f'{self.name}'

    def get_city_delivery_zones(self, city):
        return DeliveryZone.objects.filter(
            city=city
            ).all()


class Restaurant(models.Model):
    """ Модель для ресторана."""
    city = models.CharField(
        max_length=20,
        verbose_name="город",
        choices=settings.CITY_CHOICES
    )
    short_name = models.CharField(
        max_length=20,
        verbose_name='название'
    )
    address = models.CharField(
        max_length=200,
        verbose_name='адрес'
    )
    coordinates = PointField(
        blank=True,
        null=True,
        verbose_name='координаты'
    )

    open_time = models.TimeField(
        verbose_name='время открытия'
    )

    close_time = models.TimeField(
        verbose_name='время закрытия'
    )

    phone = PhoneNumberField(
        verbose_name='телефон',
        unique=True,
        blank=True, null=True,
        help_text="Внесите телефон, прим. '+38212345678'. Для пустого значения, внесите 'None'.",
    )
    admin = models.CharField(
        max_length=100,
        verbose_name='админ',
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name='активен'
    )
    image = models.ImageField(
        upload_to='contacts/',
        null=True,
        default=None,
        blank=True,
        verbose_name='Изображение',
    )
    is_overloaded = models.BooleanField(
        default=False,
        verbose_name='перегружен'
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name='ПО ДЕФОЛТУ'
    )

    def admin_photo(self):
        if self.image:
            return mark_safe(
                '<img src="{}" width="100" />'.format(self.image.url)
                )
        missing_image_url = "icons/missing_image.jpg"
        return mark_safe(
            '<img src="{}" width="100" />'.format(missing_image_url)
            )

    admin_photo.short_description = 'Image'
    admin_photo.allow_tags = True

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.short_name

    def save(self, *args, **kwargs):
        lat, lon, status = google_validate_address_and_get_coordinates(self.address)
        self.coordinates = Point(lon, lat)
        return super().save()

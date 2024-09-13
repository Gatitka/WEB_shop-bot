from collections.abc import Iterable
from datetime import time
from decimal import Decimal

import requests
from django.conf import settings  # для импорта городов
from django.contrib.auth import get_user_model
from django.contrib.gis.db.models import MultiPolygonField, PointField
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.safestring import mark_safe
from parler.models import TranslatableModel, TranslatedFields
from phonenumber_field.modelfields import PhoneNumberField
from django_summernote.fields import SummernoteTextField


from web_shop_with_bots.settings import GOOGLE_API_KEY


from .utils import google_validate_address_and_get_coordinates


class Delivery(TranslatableModel):
    translations = TranslatedFields(
        description=SummernoteTextField(),
        # description=models.TextField(
        #     max_length=400,
        #     verbose_name='Описание',
        #     null=True,
        #     blank=True
        # ),
    )
    city = models.CharField(
        max_length=20,
        verbose_name="Город *",
        choices=settings.CITY_CHOICES
    )
    type = models.CharField(
        max_length=8,
        verbose_name="Тип *",
        choices=settings.DELIVERY_CHOICES
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
        verbose_name='MIN время выдачи',
        default=time(11, 00),
        null=True,
        blank=True
        )
    max_time = models.TimeField(
        verbose_name='MAX время выдачи',
        default=time(22, 00),
        null=True,
        blank=True
        )
    min_acc_time = models.TimeField(
        verbose_name="Время открытия 'Сегодня/Как можно быстрее'",
        default=time(11, 00),
        help_text='MIN время приема заказов на сегодня',
        null=True,
        blank=True
        )
    max_acc_time = models.TimeField(
        verbose_name="Время закрытия 'Сегодня/Как можно быстрее'",
        default=time(21, 50),
        help_text='MAX время приема заказов на сегодня',
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
        return f'{self.type} {self.city}'

    def get_workhours(self):
        """ Возвращаем строку с временными рамками выдачи заказов
        для доставки/самовывоза."""
        min_time = self.min_time
        max_time = self.max_time

        min_time_str = min_time.strftime('%H:%M')
        max_time_str = max_time.strftime('%H:%M')

        return f"{min_time_str} - {max_time_str}"

    def get_acctodayhours(self):
        """ Возвращаем строку с временными рамками приема заказов
        на Сегодня/Как можно быстрее."""
        min_time = self.min_acc_time
        max_time = self.max_acc_time

        min_time_str = min_time.strftime('%H:%M')
        max_time_str = max_time.strftime('%H:%M')

        return f"{min_time_str} - {max_time_str}"

    def save(self, *args, **kwargs):
        # Проверяем тип и устанавливаем time в 00:00:00, если тип "takeaway"
        if self.type == "takeaway":
            self.min_acc_time = time(0, 0, 0)
            self.max_acc_time = time(0, 0, 0)
            self.min_time = time(0, 0, 0)
            self.max_time = time(0, 0, 0)

        # Вызываем стандартное сохранение модели
        super().save(*args, **kwargs)


class DeliveryZone(models.Model):
    """ Модель для стоимости доставки по районам."""
    city = models.CharField(
        max_length=20,
        verbose_name="город",
        choices=settings.CITY_CHOICES,
        null=True, blank=True
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
        verbose_name = 'зона доставки'
        verbose_name_plural = 'зоны доставки'

    def __str__(self):
        if self.name in ['уточнить', 'по запросу']:
            return f'{self.name}'
        else:
            return f'{self.name}, {self.delivery_cost}/ {self.city}'

    def get_city_delivery_zones(self, city):
        return DeliveryZone.objects.filter(
            city=city
            ).all()

    def save(self, *args, **kwargs):
        # Проверка, если name == 'уточнить' или 'по запросу', то город обязателен
        if self.name not in ['уточнить', 'по запросу'] and not self.city:
            raise ValidationError("Для зоны необходимо выбрать город.")
        super().save(*args, **kwargs)


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

    min_acc_time = models.TimeField(
        verbose_name="Время открытия 'Сегодня/Как можно быстрее'",
        default=time(11, 00),
        help_text='MIN время приема заказов на сегодня',
        null=True,
        blank=True
        )
    max_acc_time = models.TimeField(
        verbose_name="Время закрытия 'Сегодня/Как можно быстрее'",
        default=time(21, 50),
        help_text='MAX время приема заказов на сегодня',
        null=True,
        blank=True
        )

    phone = PhoneNumberField(
        verbose_name='телефон',
        unique=True,
        blank=True, null=True,
        help_text="Внесите телефон, прим. '+38212345678'. Для пустого значения, внесите 'None'.",
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
        verbose_name='ПО ДЕФОЛТУ для города'
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
        return f'{self.city}/{self.address[0:10]}'

    def save(self, *args, **kwargs):
        lat, lon, status = google_validate_address_and_get_coordinates(
                                                                self.address,
                                                                self.city)
        self.coordinates = Point(lon, lat)
        return super().save()

    def get_workhours(self):
        # Извлекаем координаты из объекта модели и сериализуем их без SRID
        min_time = self.open_time
        max_time = self.close_time

        min_time_str = min_time.strftime('%H:%M')
        max_time_str = max_time.strftime('%H:%M')

        return f"{min_time_str} - {max_time_str}"

    def get_acctodayhours(self):
        """ Возвращаем строку с временными рамками приема заказов
        на Сегодня/Как можно быстрее."""
        min_time = self.min_acc_time
        max_time = self.max_acc_time

        min_time_str = min_time.strftime('%H:%M')
        max_time_str = max_time.strftime('%H:%M')

        return f"{min_time_str} - {max_time_str}"

    def get_admin(self):
        """ Возвращаем админа ресторана."""
        return self.admin.all()


class Courier(models.Model):
    city = models.CharField(
        max_length=20,
        verbose_name="город",
        choices=settings.CITY_CHOICES
    )
    name = models.CharField(
        max_length=20,
        verbose_name='Имя'
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name='активен'
    )

    def __str__(self):
        return self.name

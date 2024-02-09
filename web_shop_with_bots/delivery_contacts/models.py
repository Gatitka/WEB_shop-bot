from collections.abc import Iterable
from decimal import Decimal

import requests
from django.db import models
from django.contrib.gis.db.models import PointField, MultiPolygonField

from django.utils.safestring import mark_safe

from web_shop_with_bots.settings import GOOGLE_API_KEY
from parler.models import TranslatableModel, TranslatedFields

from django.conf import settings  # для импорта городов
from phonenumber_field.modelfields import PhoneNumberField
from django.core.validators import MinValueValidator
from django.contrib.gis.geos import Point



DELIVERY_CHOICES = (
    ("delivery", "Доставка"),
    ("takeaway", "Самовывоз")
)


class Delivery(TranslatableModel):
    translations = TranslatedFields(
        description=models.CharField(
            max_length=400,
            verbose_name='Описание',
            null=True,
            blank=True
        ),
    )
    city = models.CharField(
        max_length=20,
        verbose_name="город",
        choices=settings.CITY_CHOICES
    )
    type = models.CharField(
        max_length=8,
        verbose_name="тип",
        choices=DELIVERY_CHOICES
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name='активен'
    )
    min_order_price = models.FloatField(
        verbose_name='min_цена_заказа',
        # validators=[MinValueValidator(0.01)]
        null=True,
        blank=True
    )
    default_delivery_cost = models.DecimalField(
        verbose_name='цена, DIN',
        validators=[MinValueValidator(0.01)],
        help_text='Внесите цену в DIN. Формат 00000.00',
        max_digits=7, decimal_places=2,
        default=Decimal('0'),
        null=True,
        blank=True
    )
    discount = models.FloatField(
        verbose_name="Внесите скидку, прим. для 10% внесите '10,00'.",
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

    def get_delivery_cost(self, city, discounted_amount, address):
        """
        Рассчитывает стоимость доставки с учетом суммы заказа и адреса доставки.

        Параметры:
            discounted_amount (Decimal): Сумма заказа с учетом скидки.
            address (str): Адрес доставки.

        Возвращает:
            Decimal: Стоимость доставки для указанного адреса и суммы заказа.
        """
        # Получаем координаты адреса доставки
        lat, lon = self.get_coordinates(address)

        # Получаем все районы доставки из базы данных
        delivery_zones = DeliveryZone.objects.filter(city=self.city).all()

        # Перебираем все районы доставки и проверяем, входит ли адрес в каждый из них
        for zone in delivery_zones:
            if zone.is_point_inside(lat, lon):
                # Если адрес входит в текущий район доставки, проверяем условия промо-акции
                if zone.is_promo and discounted_amount >= zone.promo_min_order_amount:
                    # Если для района установлена промо-акция и сумма заказа больше или равна
                    # минимальной сумме для промо-акции, доставка бесплатная
                    return Decimal(0)
                else:
                    # Если промо-акция не действует или сумма заказа меньше минимальной,
                    # возвращаем стоимость доставки для данного района
                    return zone.delivery_cost

        # Если адрес не входит ни в один из районов доставки, возвращаем стоимость доставки
        # по умолчанию (например, стандартная стоимость для города)
        return self.default_delivery_cost

    def get_coordinates(self, address):
        params = {
            'key': GOOGLE_API_KEY,
            'address': address
        }

        base_url = 'https://maps.googleapis.com/maps/api/geocode/json?'

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Проверяем успешность запроса
            data = response.json()  # Парсим ответ в формате JSON

            if data['status'] == 'OK':
                geometry = data['results'][0]['geometry']
                lat = geometry['location']['lat']
                lon = geometry['location']['lng']
                return lat, lon
            else:
                # Если статус ответа не 'OK', выбрасываем исключение с сообщением об ошибке
                raise Exception(f'Ошибка получения координат:'
                                f'{data["status"]}, {address}')

        except requests.exceptions.RequestException as e:
            # Если произошла ошибка при выполнении запроса, возвращаем None
            print(f'Ошибка при запросе к API Google Maps: {e}')
            return None

        except KeyError as e:
            # Если произошла ошибка из-за отсутствия ожидаемых ключей в ответе, возвращаем None
            print(f'Ошибка при разборе ответа от API Google Maps: {e}')
            return None

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
    polygon = MultiPolygonField()

    is_promo = models.BooleanField(
        verbose_name='промо',
        default=False
    )
    promo_min_order_amount = models.DecimalField(
        verbose_name='мин сумма заказа, DIN',
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
        return f'{self.id}'


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

    work_hours = models.CharField(
        max_length=100,
        verbose_name='время работы'
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

    def save(self, force_insert: bool = ..., force_update: bool = ..., using: str | None = ..., update_fields: Iterable[str] | None = ...) -> None:
        delivery = Delivery()
        lat, lon = delivery.get_coordinates(self.address)
        self.coordinates = Point(lon, lat)
        return super().save()

from decimal import Decimal
import requests

from django.db import models
from django.utils.safestring import mark_safe
from web_shop_with_bots.settings import GOOGLE_API_KEY
# from django.contrib.gis.geos import Polygon
# from django.contrib.gis.db import models
# from django.contrib.gis.db import models

DELIVERY_CHOICES = (
    ("1", "Доставка"),
    ("2", "Самовывоз")
)

CITY_CHOICES = [
    ('Белград', 'Белград'),
    ('Нови_Сад', 'Нови_Сад'),
]

ad='Milovana Milovanovića 4'


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
        default=False,
        verbose_name='активен'
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
    discount = models.FloatField(
        verbose_name='размер скидки',
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
    city = models.CharField(
        max_length=20,
        verbose_name='город'
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

    class Meta:
        verbose_name = 'доставка'
        verbose_name_plural = 'доставки'

    def __str__(self):
        return f'{self.name_rus}'


class DistrictDeliveryCost(models.Model):
    """ Модель для стоимости доставки по районам."""
    city = models.CharField(
        max_length=20,
        verbose_name="город",
        choices=CITY_CHOICES
    )
    district = models.CharField(
        max_length=20,
        verbose_name="район",
        unique=True,
    )
    promo = models.BooleanField(
        verbose_name='промо',
        default=False
    )
    min_order_amount = models.DecimalField(
        verbose_name='мин сумма заказа, DIN',
        default=0.00,
        blank=True,
        max_digits=10, decimal_places=2
    )
    delivery_cost = models.DecimalField(
        verbose_name='стоимость доставки, DIN',
        default=0.00,
        blank=True,
        max_digits=10, decimal_places=2
    )
    # district_pol = models.PolygonField(
    #     max_length=20,
    #     verbose_name="полигон",
    #     unique=True,
    #     blank=True, null=True
    # )

    def get_delivery_cost(self, discontinued_amount, recipient_district):
        """
        Рассчитывает delivery_cost с учетом суммы заказа.
        """
        if (recipient_district.promo
                and discontinued_amount >= recipient_district.min_order_amount):
            # Если район имеет промо предложение, и сумма заказа больше мин суммы,
            # доставка бесплатная
            return Decimal(0)
        return recipient_district.delivery_cost

    def get_delivery_cost2(self, address, discounted_amount):
        params = {
            'key': GOOGLE_API_KEY,
            'address': address
        }

        base_url = 'https://maps.googleapis.com/maps/api/geocode/json?'
        responce = requests.get(base_url, params=params).json()
        print(responce)
        responce.keys()

        if responce['status'] == 'OK':
            geometry = responce['results'][0]['geometry']
            lat = geometry['location']['lat']
            lon = geometry['location']['lng']
        print(lat,lon)


    class Meta:
        verbose_name = 'район доставки'
        verbose_name_plural = 'районы доставки'

    def __str__(self):
        return f'{self.district}'


# polygon = Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)))
# DistrictDeliveryCost.objects.create(polygon=polygon)


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
        default=False,
        verbose_name='активен'
    )
    city = models.CharField(
        max_length=50,
        verbose_name='город',
        blank=True,
        null=True
    )
    image = models.ImageField(
        upload_to='contacts/',
        null=True,
        default=None,
        blank=True,
        verbose_name='Изображение',
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
        return f'{self.short_name}'

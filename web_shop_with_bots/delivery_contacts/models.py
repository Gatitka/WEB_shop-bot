from django.db import models


DELIVERY_CHOICES = (
    ("1", "Доставка"),
    ("2", "Самовывоз")
)


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

    class Meta:
        verbose_name = 'доставка'
        verbose_name_plural = 'доставка'

    def __str__(self):
        return f'{self.name_rus}'


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
    # map_location = картинка карты

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return f'{self.short_name}'

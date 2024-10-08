# Generated by Django 4.0 on 2024-09-19 05:38

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery_contacts', '0021_alter_deliveryzone_city_alter_restaurant_is_default'),
    ]

    operations = [
        migrations.AlterField(
            model_name='delivery',
            name='max_acc_time',
            field=models.TimeField(blank=True, default=datetime.time(21, 50), help_text=('MAX время приема заказов на сегодня.<br>', 'прим, для Доставки - 21:50,<br>для Самовывоза - 00:00, т.к. время берется из аналогичных данных ресторана.'), null=True, verbose_name="Время закрытия 'Сегодня/Как можно быстрее'"),
        ),
        migrations.AlterField(
            model_name='delivery',
            name='max_time',
            field=models.TimeField(blank=True, default=datetime.time(22, 0), help_text=('Самое позднее время выдачи заказа.<br>прим, для Доставки - 22:00,<br>для Самовывоза - 00:00, т.к. время берется из аналогичных данных ресторана.',), null=True, verbose_name='MAX время выдачи'),
        ),
        migrations.AlterField(
            model_name='delivery',
            name='min_acc_time',
            field=models.TimeField(blank=True, default=datetime.time(11, 0), help_text=('MIN время приема заказов на Сегодня/Как можно быстрее.<br>прим, для Доставки - 11:00,<br>для Самовывоза - 00:00, т.к. время берется из аналогичных данных ресторана.',), null=True, verbose_name="Время открытия 'Сегодня/Как можно быстрее'"),
        ),
        migrations.AlterField(
            model_name='delivery',
            name='min_time',
            field=models.TimeField(blank=True, default=datetime.time(11, 0), help_text=('Самое ранне время выдачи заказа.<br>прим, для Доставки - 11:30,<br>для Самовывоза - 00:00, т.к. время берется из аналогичных данных ресторана.',), null=True, verbose_name='MIN время выдачи'),
        ),
        migrations.AlterField(
            model_name='deliveryzone',
            name='is_promo',
            field=models.BooleanField(default=False, help_text='Наличие промо-предложения по бесплатной доставке, если заказ выше пороговой суммы.<br>Если PROMO не выбран, то заполненная мин сумма заказа не будет действовать.', verbose_name='PROMO'),
        ),
        migrations.AlterField(
            model_name='deliveryzone',
            name='promo_min_order_amount',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Если выбран PROMO, то заказы выше пороговой суммы будут иметь бесплатную доставку.<br>Сумма заказа = сумма выбранных блюд.<br>(если у блюда есть скидка, то она учитывается).<br>', max_digits=10, null=True, verbose_name='PROMO мин сумма заказа, DIN'),
        ),
    ]

# Generated by Django 4.0 on 2024-08-23 11:22

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery_contacts', '0017_restaurant_max_acc_time_restaurant_min_acc_time_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='delivery',
            name='max_acc_time',
            field=models.TimeField(blank=True, default=datetime.time(21, 50), help_text='MAX время приема заказов на сегодня', null=True, verbose_name="Время закрытия 'Сегодня/Как можно быстрее'"),
        ),
        migrations.AlterField(
            model_name='delivery',
            name='min_acc_time',
            field=models.TimeField(blank=True, default=datetime.time(11, 0), help_text='MIN время приема заказов на сегодня', null=True, verbose_name="Время открытия 'Сегодня/Как можно быстрее'"),
        ),
    ]

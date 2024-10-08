# Generated by Django 4.0 on 2024-08-16 12:07

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery_contacts', '0016_alter_delivery_max_acc_time_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='restaurant',
            name='max_acc_time',
            field=models.TimeField(blank=True, default=datetime.time(21, 50), help_text='MAX время приема заказов на сегодня', null=True, verbose_name="Время закрытия 'Сегодня/Как можно быстрее'"),
        ),
        migrations.AddField(
            model_name='restaurant',
            name='min_acc_time',
            field=models.TimeField(blank=True, default=datetime.time(11, 0), help_text='MIN время приема заказов на сегодня', null=True, verbose_name="Время открытия 'Сегодня/Как можно быстрее'"),
        ),
        migrations.AlterField(
            model_name='delivery',
            name='max_acc_time',
            field=models.TimeField(blank=True, default=datetime.time(21, 50), help_text='MAX время приема заказов на доставку', null=True, verbose_name="Время закрытия 'Сегодня/Как можно быстрее'"),
        ),
    ]

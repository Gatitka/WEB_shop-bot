# Generated by Django 4.0 on 2024-07-29 15:07

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery_contacts', '0013_alter_courier_city_alter_delivery_city_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='delivery',
            name='max_time',
            field=models.TimeField(blank=True, default=datetime.time(22, 0), null=True, verbose_name='MAX время заказа'),
        ),
        migrations.AlterField(
            model_name='delivery',
            name='min_time',
            field=models.TimeField(blank=True, default=datetime.time(11, 0), null=True, verbose_name='MIN время заказа'),
        ),
    ]
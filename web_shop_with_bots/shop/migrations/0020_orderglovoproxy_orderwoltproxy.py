# Generated by Django 4.0 on 2024-05-20 12:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0019_order_courier'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderGlovoProxy',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('shop.order',),
        ),
        migrations.CreateModel(
            name='OrderWoltProxy',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('shop.order',),
        ),
    ]

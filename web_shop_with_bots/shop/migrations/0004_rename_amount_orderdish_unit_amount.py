# Generated by Django 4.0 on 2024-04-07 23:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0003_order_user_orderdish_dish_orderdish_order_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='orderdish',
            old_name='amount',
            new_name='unit_amount',
        ),
    ]

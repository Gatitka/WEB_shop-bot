# Generated by Django 4.0 on 2024-04-17 13:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0010_rename_cash_discount_order_cash_discount_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='discount',
            name='type',
            field=models.CharField(choices=[('1', 'first_order'), ('2', 'cash_on_delivery')], max_length=20, unique=True, verbose_name='тип скидки'),
        ),
    ]
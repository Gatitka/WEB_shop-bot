# Generated by Django 4.0 on 2024-05-19 12:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0016_alter_order_origin_alter_order_recipient_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='source_id',
            field=models.CharField(blank=True, help_text='ID заказа в системе-источнике.', max_length=20, null=True, verbose_name='ID источника'),
        ),
    ]
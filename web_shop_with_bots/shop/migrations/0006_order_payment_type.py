# Generated by Django 4.0 on 2024-02-26 16:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0005_alter_order_recipient_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_type',
            field=models.CharField(blank=True, choices=[('1', 'cash'), ('2', 'card')], max_length=20, null=True, verbose_name='способ оплаты'),
        ),
    ]
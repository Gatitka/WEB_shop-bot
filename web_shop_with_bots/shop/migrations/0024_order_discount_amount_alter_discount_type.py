# Generated by Django 4.0 on 2024-05-27 15:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0023_order_auth_fst_ord_disc_order_cash_discount_disc_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=0, help_text='рассчитывается автоматически.', max_digits=8, null=True, verbose_name='размер скидки, DIN'),
        ),
        migrations.AlterField(
            model_name='discount',
            name='type',
            field=models.CharField(choices=[('1', 'first_order'), ('2', 'cash_on_delivery'), ('3', 'takeaway'), ('4', 'instagram_story'), ('5', 'birthday')], max_length=20, unique=True, verbose_name='тип скидки'),
        ),
    ]
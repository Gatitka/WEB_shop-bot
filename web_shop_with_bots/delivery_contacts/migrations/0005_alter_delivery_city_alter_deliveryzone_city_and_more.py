# Generated by Django 4.0 on 2024-02-19 13:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery_contacts', '0004_alter_delivery_default_delivery_cost_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='delivery',
            name='city',
            field=models.CharField(choices=[('Beograd', 'Beograd'), ('Novi_sad', 'Novi Sad')], max_length=20, verbose_name='Город *'),
        ),
        migrations.AlterField(
            model_name='deliveryzone',
            name='city',
            field=models.CharField(choices=[('Beograd', 'Beograd'), ('Novi_sad', 'Novi Sad')], max_length=20, verbose_name='город'),
        ),
        migrations.AlterField(
            model_name='restaurant',
            name='city',
            field=models.CharField(choices=[('Beograd', 'Beograd'), ('Novi_sad', 'Novi Sad')], max_length=20, verbose_name='город'),
        ),
    ]

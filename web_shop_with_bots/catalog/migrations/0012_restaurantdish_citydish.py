# Generated by Django 4.0 on 2024-08-23 11:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('delivery_contacts', '0018_alter_delivery_max_acc_time_and_more'),
        ('catalog', '0011_alter_dish_final_price_alter_dish_final_price_p1_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='RestaurantDish',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dish', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='restaurantdishes', to='catalog.dish', verbose_name='Активные блюда ресторана')),
                ('restaurant', models.ForeignKey(blank=True, default=1, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='restaurantdishes', to='delivery_contacts.restaurant', verbose_name='ресторан')),
            ],
        ),
        migrations.CreateModel(
            name='CityDish',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('city', models.CharField(choices=[('Beograd', 'Beograd'), ('NoviSad', 'Novi Sad')], default='Beograd', max_length=20, verbose_name='город')),
                ('dish', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='citydishes', to='catalog.dish', verbose_name='Активные блюда города')),
            ],
        ),
    ]
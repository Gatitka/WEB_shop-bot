# Generated by Django 4.0 on 2024-08-23 12:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery_contacts', '0018_alter_delivery_max_acc_time_and_more'),
        ('catalog', '0013_alter_citydish_options_alter_restaurantdish_options'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='CityDish',
            new_name='CityDishItem',
        ),
        migrations.AlterUniqueTogether(
            name='citydishitem',
            unique_together={('city', 'dish')},
        ),
        migrations.AlterUniqueTogether(
            name='restaurantdish',
            unique_together={('restaurant', 'dish')},
        ),
        migrations.CreateModel(
            name='CityDishList',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='Название')),
                ('city', models.CharField(choices=[('Beograd', 'Beograd'), ('NoviSad', 'Novi Sad')], default='Beograd', max_length=20, verbose_name='город')),
                ('dish', models.ManyToManyField(to='catalog.Dish')),
            ],
            options={
                'verbose_name': 'Блюдо / Город',
                'verbose_name_plural': 'Блюда / Город',
            },
        ),
    ]
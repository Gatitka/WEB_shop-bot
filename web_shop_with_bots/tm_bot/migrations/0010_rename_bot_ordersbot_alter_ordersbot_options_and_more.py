# Generated by Django 4.0 on 2024-09-04 17:50

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('delivery_contacts', '0020_remove_restaurant_admin'),
        ('tm_bot', '0009_bot_messengeraccount_city'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Bot',
            new_name='OrdersBot',
        ),
        migrations.AlterModelOptions(
            name='ordersbot',
            options={'ordering': ['city'], 'verbose_name': 'Бот д/приема заказов', 'verbose_name_plural': 'Боты д/приема заказов'},
        ),
        migrations.CreateModel(
            name='AdminChatTM',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chat_id', models.CharField(blank=True, help_text='Получить через BotFather.', max_length=100, null=True, unique=True, validators=[django.core.validators.MinLengthValidator(4)], verbose_name='ID чата в ТМ')),
                ('city', models.CharField(blank=True, choices=[('Beograd', 'Beograd'), ('NoviSad', 'Novi Sad')], default='Beograd', max_length=40, null=True, verbose_name='город *')),
                ('restaurant', models.ForeignKey(blank=True, default=1, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='admin_chat', to='delivery_contacts.restaurant', verbose_name='ресторан')),
            ],
            options={
                'verbose_name': 'Админ-чат TM',
                'verbose_name_plural': 'Админ-чаты TM',
                'ordering': ['city'],
            },
        ),
    ]

# Generated by Django 4.0 on 2024-03-19 14:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_alter_webaccount_notes'),
    ]

    operations = [
        migrations.AddField(
            model_name='webaccount',
            name='role',
            field=models.CharField(choices=[('admin', 'Администратор'), ('user', 'Пользователь')], default='user', max_length=9, verbose_name='Роль'),
        ),
    ]

# Generated by Django 4.0 on 2024-06-21 22:29

from django.db import migrations, models
import users.validators


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_alter_useraddress_flat_alter_useraddress_floor_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='baseprofile',
            name='city',
            field=models.CharField(blank=True, choices=[('Beograd', 'Beograd')], default='Beograd', max_length=40, null=True, verbose_name='город *'),
        ),
        migrations.AlterField(
            model_name='baseprofile',
            name='first_name',
            field=models.CharField(blank=True, max_length=300, null=True, verbose_name='Имя'),
        ),
        migrations.AlterField(
            model_name='baseprofile',
            name='last_name',
            field=models.CharField(blank=True, max_length=300, null=True, verbose_name='Фамилия'),
        ),
        migrations.AlterField(
            model_name='baseprofile',
            name='notes',
            field=models.CharField(blank=True, max_length=1500, null=True, verbose_name='Пометки'),
        ),
        migrations.AlterField(
            model_name='useraddress',
            name='flat',
            field=models.CharField(blank=True, max_length=150, null=True, verbose_name='квартира'),
        ),
        migrations.AlterField(
            model_name='useraddress',
            name='floor',
            field=models.CharField(blank=True, max_length=150, null=True, verbose_name='этаж'),
        ),
        migrations.AlterField(
            model_name='useraddress',
            name='interfon',
            field=models.CharField(blank=True, max_length=150, null=True, verbose_name='домофон'),
        ),
        migrations.AlterField(
            model_name='webaccount',
            name='first_name',
            field=models.CharField(max_length=300, validators=[users.validators.validate_first_and_last_name], verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='webaccount',
            name='last_name',
            field=models.CharField(max_length=300, validators=[users.validators.validate_first_and_last_name], verbose_name='last_name'),
        ),
    ]

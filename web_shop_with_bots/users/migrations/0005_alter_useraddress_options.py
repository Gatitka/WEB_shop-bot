# Generated by Django 4.0 on 2024-04-16 11:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_rename_interfone_useraddress_interfon'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='useraddress',
            options={'verbose_name': 'My address', 'verbose_name_plural': 'My addresses'},
        ),
    ]
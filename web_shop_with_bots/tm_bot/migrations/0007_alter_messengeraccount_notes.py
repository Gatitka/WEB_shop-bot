# Generated by Django 4.0 on 2024-06-26 11:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tm_bot', '0006_alter_messengeraccount_msngr_id_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='messengeraccount',
            name='notes',
            field=models.TextField(blank=True, max_length=400, null=True, verbose_name='Комментарии'),
        ),
    ]
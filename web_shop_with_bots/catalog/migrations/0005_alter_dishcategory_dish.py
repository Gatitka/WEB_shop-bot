# Generated by Django 4.0 on 2024-02-23 13:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0004_alter_dishcategory_dish'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dishcategory',
            name='dish',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dishcategory', to='catalog.dish'),
        ),
    ]
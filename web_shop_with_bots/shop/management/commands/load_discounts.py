import os
import re
from csv import DictReader

from django.core.management import BaseCommand

from shop.models import Discount
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = "Loads data for discounts"

    def handle(self, *args, **options):
        # Получаем сегодняшнюю дату
        today = timezone.now().date()
        # Вычисляем дату через год
        valid_to = today + timedelta(days=365)

        first_discount, created = Discount.objects.get_or_create(
            type=1,
            discount_perc=5,
            is_active=True,
            valid_from=today,
            valid_to=valid_to,
            title_rus='5% скидка на первый заказ'
        )
        second_discount, created = Discount.objects.get_or_create(
            type=2,
            discount_perc=10,
            is_active=True,
            valid_from=today,
            valid_to=valid_to,
            title_rus='10% скидка за оплату наличными заказа с доставкой'
        )

        self.stdout.write(
            self.style.SUCCESS(
                'Load_discounts executed successfully.'
            )
        )

from django.core.management import BaseCommand
from django.core.management import call_command
from promos.models import PromoNews, Promocode
import os
from csv import DictReader
from datetime import datetime, timedelta
from django.utils import timezone


class Command(BaseCommand):
    help = "Loads all delivery_data"

    def handle(self, *args, **options):
        with open('docs/promo.csv', encoding='utf-8-sig') as f:
            for row in DictReader(f, delimiter=';'):

                if not any(row.values()):
                    continue

                promo, created = PromoNews.objects.get_or_create(
                    city=row['город'],
                    is_active=row['активно'],
                    image_ru=os.path.join('promo', row['image_ru']),
                    image_en=os.path.join('promo', row['image_en']),
                    image_sr_latn=os.path.join('promo', row['image_sr_latn']),
                )
                promo.set_current_language('ru')
                promo.title = row['заголовок_ru']
                promo.full_text = row['описание_ru']
                promo.save()

                promo.set_current_language('en')
                promo.title = row['заголовок_en']
                promo.full_text = row['описание_en']
                promo.save()

                promo.set_current_language('sr-latn')       # Only switches
                promo.title = row['заголовок_sr-latn']
                promo.full_text = row['описание_sr-latn']
                promo.save()

        self.stdout.write(
            self.style.SUCCESS(
                'Load_promo_news executed successfully.'
            )
        )

        # Получаем сегодняшнюю дату
        today = timezone.now().date()
        # Вычисляем дату через год
        valid_to = today + timedelta(days=365)

        promocode1, created = Promocode.objects.get_or_create(
            title_rus='Takeaway 10%',
            promocode='take10',
            discount=10.00,
            is_active=True,
            valid_from=today,
            valid_to=valid_to,
        )

from csv import DictReader

from django.core.management import BaseCommand

from delivery_contacts.models import Courier


class Command(BaseCommand):
    help = "Loads couriers list from couriers.csv"

    def handle(self, *args, **options):
        with open('docs/couriers.csv', encoding='utf-8-sig') as f:

            for row in DictReader(f, delimiter=';'):
                if not any(row.values()):
                    continue

                courier, _ = Courier.objects.get_or_create(
                    city=row['город'],  # Укажите ваш город
                    name=row['имя'],  # Укажите имя для зоны доставки
                    is_active=row['активно']
                )

        self.stdout.write(
            self.style.SUCCESS(
                'Load_couriers executed successfully.'
            )
        )

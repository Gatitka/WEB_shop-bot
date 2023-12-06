from csv import DictReader
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from catalog.models import Dish, Category
from shop.models import Delivery, Shop

User = get_user_model()


class Command(BaseCommand):
    help = "Loads data from menu.csv"

    def handle(self, *args, **options):

        with open('menu.csv', encoding='utf-8') as f:
            for row in DictReader(f, delimiter=';'):
                category = Category.objects.get_or_create(
                        priority=row['Раздел 1'][:2],
                        name_rus=row['Раздел 1'][4:],
                        name_srb=row['Раздел 1'][4:],
                        slug=row['slug']
                    )
                dish = Dish.objects.get_or_create(
                    short_name_rus=row['Наименование'],
                    short_name_srb=row['Наименование'],
                    text_rus=row['Описание'],
                    text_srb=row['Описание'],
                    price=row['Цена'],
                    category=category[0],
                    weight=row['Вес'],
                    article=row['Артикул'],
                    uom=row['Ед. изм'],
                    volume=row['Объем']
                )

        self.stdout.write(
            self.style.SUCCESS(
                'Load_menu executed successfully.'
            )
        )

        user1 = User.objects.get_or_create(
            email="a1@a1.ru",
            password="foreverlove"
        )
        user2 = User.objects.get_or_create(
            email="a2@a2.ru",
            password="foreverlove"
        )
        user3 = User.objects.get_or_create(
            email="a3@a3.ru",
            password="foreverlove"
        )

        delivery1 = Delivery.objects.get_or_create(
            name_rus="доставка",
            name_srb="доставка",
            name_en="доставка",
            type="1"
        )
        delivery2 = Delivery.objects.get_or_create(
            name_rus="самовывоз",
            name_srb="самовывоз",
            name_en="самовывоз",
            type="2"
        )
        shop1 = Shop.objects.get_or_create(
            short_name='центр',
            address_rus="Белград, ул.Милована Миловановича 4",
            address_srb="Белград, ул.Милована Миловановича 4",
            address_en="Белград, ул.Милована Миловановича 4",
            work_hours="9:00 - 22:00",
            phone="+381 61 271 4798"
        )

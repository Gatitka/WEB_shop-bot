from csv import DictReader
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from catalog.models import Dish, Category
from shop.models import Delivery, Shop
from users.models import UserAddresses, BaseProfile, WEBAccount


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

        admin = User.objects.get_or_create(
            email="a@a.ru",
            is_active=True,
            is_superuser=True,
            is_staff=1
        )
        admin=admin[0]
        admin.set_password("admin")
        admin.save()

        user1 = User.objects.get_or_create(
            email="a1@a1.ru",
        )
        user1=user1[0]
        user1.set_password("foreverlove")
        user1.save()
        user2 = User.objects.get_or_create(
            email="a2@a2.ru",
        )
        user2=user2[0]
        user2.set_password("foreverlove")
        user2.save()
        user3 = User.objects.get_or_create(
            email="a3@a3.ru",
        )
        user3=user3[0]
        user3.set_password("foreverlove")
        user3.save()

        delivery1 = Delivery.objects.get_or_create(
            name_rus="доставка",
            name_srb="доставка",
            name_en="доставка",
            type="1",
            city='Белград'
        )
        delivery2 = Delivery.objects.get_or_create(
            name_rus="самовывоз",
            name_srb="самовывоз",
            name_en="самовывоз",
            type="2",
            city='Белград'
        )
        shop1 = Shop.objects.get_or_create(
            short_name='центр',
            address_rus="ул.Милована Миловановича 4",
            address_srb="ул.Милована Миловановича 4",
            address_en="ул.Милована Миловановича 4",
            work_hours="9:00 - 22:00",
            phone="+381 61 271 4798",
            city='Белград'
        )
        shop2 = Shop.objects.get_or_create(
            short_name='центр2',
            address_rus="ул.Хуливана Хуливановича 4",
            address_srb="ул.Хуливана Хуливановича 4",
            address_en="ул.Хуливана Хуливановича 4",
            work_hours="9:00 - 22:00",
            phone="+381 11 222 3333",
            city='Белград'
        )
        shop3 = Shop.objects.get_or_create(
            short_name='НовиСад',
            address_rus="ул.Хуливана Хуливановича 4",
            address_srb="ул.Хуливана Хуливановича 4",
            address_en="ул.Хуливана Хуливановича 4",
            work_hours="9:00 - 22:00",
            phone="+381 22 222 3333",
            city='Нови Сад'
        )

        address1 = UserAddresses.objects.get_or_create(
            base_profile=user1.base_profile,
            short_name="адрес1",
            city='Belgrade',
            full_address="ул.Милована Миловановича 1",
            type="1"
        )
        address2 = UserAddresses.objects.get_or_create(
            base_profile=user1.base_profile,
            short_name="адрес2",
            city='Belgrade',
            full_address="ул.Милована Миловановича 2",
            type="2"
        )
        address3 = UserAddresses.objects.get_or_create(
            base_profile=user2.base_profile,
            short_name="адрес3",
            city='Belgrade',
            full_address="ул.Милована Миловановича 3",
            type="1"
        )
        address4 = UserAddresses.objects.get_or_create(
            base_profile=user2.base_profile,
            short_name="адрес4",
            city='Belgrade',
            full_address="ул.Милована Миловановича 4",
            type="1"
        )

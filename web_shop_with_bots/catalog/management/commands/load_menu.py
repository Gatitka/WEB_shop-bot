from csv import DictReader
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from catalog.models import Dish, Category
from shop.models import Delivery, Shop
from users.models import UserAddress, BaseProfile, WEBAccount
from promos.models import PromoNews
from delivery_contacts.models import Shop, Delivery


User = get_user_model()


class Command(BaseCommand):
    help = "Loads data from menu.csv"

    def handle(self, *args, **options):

        with open('menu.csv', encoding='utf-8') as f:
            for row in DictReader(f, delimiter=';'):
                if not any(row.values()):
                    continue
                vegan_cat = Category.objects.get_or_create(
                        priority=20,
                        name_rus='Веган',
                        name_srb='Веган',
                        slug='vegan',
                        is_active=True,
                    )[0]
                category = Category.objects.get_or_create(
                        priority=row['пп кат'],
                        name_rus=row['Раздел 1'][4:],
                        name_srb=row['Раздел 1'][4:],
                        slug=row['slug'],
                        is_active=True,
                    )[0]
                dish = Dish.objects.get_or_create(
                    priority=row['пп блюд'],
                    short_name_rus=row['Наименование'],
                    short_name_srb=row['Наименование'],
                    text_rus=row['Описание'],
                    text_srb=row['Описание'],
                    price=row['Цена'],
                    weight=row['Вес'],
                    article=row['Артикул'],
                    uom=row['Ед. изм'],
                    volume=row['Объем'],
                    vegan_icon=row['vegan icon'],
                    spicy_icon=row['hot icon'],
                    is_active=True,
                )[0]
                cat = (category,)
                if self.vegan_icon == True:
                    cat = (category, vegan_cat)
                dish.category.set(cat)

        admin = User.objects.get_or_create(
            email="a@a.ru",
            is_active=True,
            is_superuser=True,
            is_staff=1,
            first_name='admin',
            phone='+79055969166'
        )
        admin=admin[0]
        admin.set_password("admin")
        admin.save()

        user1 = User.objects.get_or_create(
            email="a1@a1.ru",
            first_name='Петя',
            phone='+79055969160'
        )
        user1=user1[0]
        user1.set_password("foreverlove")
        user1.save()

        user2 = User.objects.get_or_create(
            email="a2@a2.ru",
            first_name='Вася',
            phone='+79055969161',
        )
        user2=user2[0]
        user2.set_password("foreverlove")
        user2.save()

        user3 = User.objects.get_or_create(
            email="a3@a3.ru",
            first_name='Коля',
            phone='+79055969162'
        )
        user3=user3[0]
        user3.set_password("foreverlove")
        user3.save()

        delivery1 = Delivery.objects.get_or_create(
            name_rus="доставка",
            name_srb="доставка",
            name_en="доставка",
            type="1",
            city='Белград',
            is_active=True,
        )
        delivery2 = Delivery.objects.get_or_create(
            name_rus="самовывоз",
            name_srb="самовывоз",
            name_en="самовывоз",
            type="2",
            city='Белград',
            is_active=True,
        )
        shop1 = Shop.objects.get_or_create(
            short_name='центр',
            address_rus="ул.Милована Миловановича 4",
            address_srb="ул.Милована Миловановича 4",
            address_en="ул.Милована Миловановича 4",
            work_hours="9:00 - 22:00",
            phone="+381 61 271 4798",
            city='Белград',
            is_active=True,
        )
        shop2 = Shop.objects.get_or_create(
            short_name='центр2',
            address_rus="ул.Хуливана Хуливановича 4",
            address_srb="ул.Хуливана Хуливановича 4",
            address_en="ул.Хуливана Хуливановича 4",
            work_hours="9:00 - 22:00",
            phone="+381 11 222 3333",
            city='Белград',
            is_active=True,
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

        address1 = UserAddress.objects.get_or_create(
            base_profile=user1.base_profile,
            short_name="адрес1",
            city='Belgrade',
            full_address="ул.Милована Миловановича 1",
            type="1"
        )
        address2 = UserAddress.objects.get_or_create(
            base_profile=user1.base_profile,
            short_name="адрес2",
            city='Belgrade',
            full_address="ул.Милована Миловановича 2",
            type="2"
        )
        address3 = UserAddress.objects.get_or_create(
            base_profile=user2.base_profile,
            short_name="адрес3",
            city='Belgrade',
            full_address="ул.Милована Миловановича 3",
            type="1"
        )
        address4 = UserAddress.objects.get_or_create(
            base_profile=user2.base_profile,
            short_name="адрес4",
            city='Belgrade',
            full_address="ул.Милована Миловановича 4",
            type="1"
        )

        promo1 = PromoNews.objects.get_or_create(
            title_rus='самовывоз 10%',
            full_text_rus='при заказе от 2500 самовывоз',
            city='Belgrade',
            is_active=True,
        )

        promo2 = PromoNews.objects.get_or_create(
            title_rus='авокадо',
            full_text_rus='новые суши с авокадо',
            city='Belgrade',
            is_active=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                'Load_menu executed successfully.'
            )
        )

import os
import re
from csv import DictReader

from django.core.management import BaseCommand

from catalog.models import UOM, Category, Dish
from web_shop_with_bots.settings import BASE_DIR


def find_image_by_article(article):
            # Укажите путь к директории с изображениями
            image_directory = os.path.join(BASE_DIR,
                                           'media', 'menu', 'dish_images')
            # Формируем регулярное выражение для поиска файлов по артикулу
            pattern = re.compile(rf"{article} .*\.jpg", re.IGNORECASE)

            # Перебираем файлы в директории
            for filename in os.listdir(image_directory):
                if pattern.match(filename):
                    # Найдено соответствие, возвращаем путь к файлу
                    return os.path.join('menu', 'dish_images', filename)

            # Если файл не найден
            return os.path.join('icons', 'missing_image.jpg')


class Command(BaseCommand):
    help = "Loads data from menu.csv"

    def handle(self, *args, **options):

        def find_image_by_article(article):
            # Укажите путь к директории с изображениями
            image_directory = os.path.join(BASE_DIR,
                                           'media', 'menu', 'dish_images')
            # Формируем регулярное выражение для поиска файлов по артикулу
            pattern = re.compile(rf"{article} .*\.jpg", re.IGNORECASE)

            # Перебираем файлы в директории
            for filename in os.listdir(image_directory):
                if pattern.match(filename):
                    # Найдено соответствие, возвращаем путь к файлу
                    return os.path.join('menu', 'dish_images', filename)

            # Если файл не найден
            return os.path.join('icons', 'missing_image.jpg')

        with open('docs/uom.csv', encoding='utf-8-sig') as f:
            for row in DictReader(f, delimiter=';'):
                if not any(row.values()):
                    continue

                uom, created = UOM.objects.get_or_create(
                    name=row['name']
                )
                uom.set_current_language('ru')
                uom.text = row['ru']
                uom.save()
                uom.set_current_language('en')
                uom.text = row['en']
                uom.save()
                uom.set_current_language('sr-latn')
                uom.text = row['sr-latn']
                uom.save()

        self.stdout.write(
            self.style.SUCCESS(
                'Load UOM executed successfully.'
            )
        )

        with open('docs/categories.csv', encoding='utf-8-sig') as f:
            for row in DictReader(f, delimiter=';'):
                if not any(row.values()):
                    continue

                category, created = Category.objects.get_or_create(
                        priority=row['пп кат'],
                        slug=row['slug'],
                        is_active=row['активно'],
                    )
                category.set_current_language('ru')
                category.name = row['категория_ru']
                category.save()
                category.set_current_language('en')
                category.name = row['категория_en']
                category.save()
                category.set_current_language('sr-latn')
                category.name = row['категория_sr_latn']
                category.save()

        self.stdout.write(
            self.style.SUCCESS(
                'Load CATEGORY executed successfully.'
            )
        )

        with open('docs/menu.csv', encoding='utf-8-sig') as f:
            vegan_cat = Category.objects.get(slug='vegan')

            for row in DictReader(f, delimiter=';'):
                if not any(row.values()):
                    continue

                article_number = row['Артикул']
                image_path = find_image_by_article(article_number)
                vegan_icon = bool(row['vegan icon'])

                spicy_icon = bool(row['hot icon'])

                dish, created = Dish.objects.get_or_create(
                    article=row['Артикул'],
                    is_active=row['Активно'],
                    priority=row['пп блюд'],
                    price=row['Цена'],
                    weight_volume=row['вес/объем'],
                    weight_volume_uom=UOM.objects.get(
                        name=row['ед-цы веса/объема']
                    ),

                    units_in_set=row['кол-во в позиции'],
                    units_in_set_uom=UOM.objects.get(
                        name=row['ед-цы кол-ва']
                    ),
                    vegan_icon=vegan_icon,
                    spicy_icon=spicy_icon,
                    image=image_path,
                )

                category = Category.objects.get(slug=row['cat_slug'])
                if dish.vegan_icon and category.slug != 'extra':
                    dish.category.set([category, vegan_cat])
                else:
                    dish.category.set([category])

                dish.set_current_language('ru')
                dish.short_name = row['наименование_ru']
                dish.text = row['описание_ru']
                dish.save()

                dish.set_current_language('en')
                dish.short_name = row['наименование_en']
                dish.text = row['описание_en']
                dish.save()

                dish.set_current_language('sr-latn')       # Only switches
                dish.short_name = row['наименование_sr_latn']
                dish.text = row['описание_sr_latn']
                dish.save()

        self.stdout.write(
            self.style.SUCCESS(
                'Load DISH executed successfully.'
            )
        )

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

                uom, uom_created = UOM.objects.get_or_create(
                    name=row['name']
                )

                if uom_created:
                    translations = {
                        'ru': row['ru'],
                        'en': row['en'],
                        'sr_latn': row['sr-latn']
                    }

                    for language_code, translation in translations.items():
                        uom.set_current_language(language_code)
                        uom.text = translation
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

                category, category_created = Category.objects.get_or_create(
                        priority=row['пп кат'],
                        slug=row['slug'],
                        is_active=row['активно'],
                    )
                if category_created:
                    translations = {
                        'ru': row['категория_ru'],
                        'en': row['категория_en'],
                        'sr-latn': row['категория_sr_latn']
                    }

                    for language_code, translation in translations.items():
                        category.set_current_language(language_code)
                        category.name = translation

                    category.save()

        self.stdout.write(
            self.style.SUCCESS(
                'Load CATEGORY executed successfully.'
            )
        )

        with open('docs/menu.csv', encoding='utf-8-sig') as f:
            vegan_cat = Category.objects.get(slug='vegan')

            for row in DictReader(f, delimiter=','):
                if not any(row.values()):
                    continue

                article_number = row['Артикул']
                image_path = find_image_by_article(article_number)
                vegan_icon = bool(row['vegan icon'])

                spicy_icon = bool(row['hot icon'])

                dish, dish_created = Dish.objects.get_or_create(
                    article=str(row['Артикул']),
                    is_active=row['Активно'],
                    priority=row['пп блюд'],
                    price=row['Цена'],
                    final_price_p1=row['Цена P1'],
                    final_price_p2=row['Цена P2'],
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
                    utensils=row['Приборы']
                )

                if dish_created:
                    category = Category.objects.get(slug=row['cat_slug'])
                    if dish.vegan_icon and category.slug != 'extra':
                        dish.category.set([category, vegan_cat])
                    else:
                        dish.category.set([category])

                    translations = {
                        'ru': {'short_name': row['наименование_ru'],
                               'text': row['описание_ru'],
                               'msngr_short_name': row['мсджр_наименование_ru'],
                               'msngr_text': row['мсджр_описание_ru']},
                        'en': {'short_name': row['наименование_en'],
                               'text': row['описание_en'],
                               'msngr_short_name': row['мсджр_наименование_en'],
                               'msngr_text': row['мсджр_описание_en']},
                        'sr-latn': {
                            'short_name': row['наименование_sr_latn'],
                            'text': row['описание_sr_latn'],
                            'msngr_short_name':
                                row['мсджр_наименование_sr_latn'],
                            'msngr_text': row['мсджр_описание_sr_latn']},
                    }

                    for language_code, translation_data in translations.items():
                        dish.set_current_language(language_code)
                        dish.short_name = translation_data['short_name']
                        dish.text = translation_data['text']

                        dish.save()

        self.stdout.write(
            self.style.SUCCESS(
                'Load DISH executed successfully.'
            )
        )

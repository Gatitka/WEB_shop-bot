from csv import DictReader

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.core.management import BaseCommand

from delivery_contacts.models import DeliveryZone


# class Command(BaseCommand):
#     help = "Loads data from delivery_zones.csv"

#     def handle(self, *args, **options):
#         with open('docs/delivery_zones.csv', encoding='utf-8-sig') as f:
#             for row in DictReader(f, delimiter=';'):
#                 if not any(row.values()):
#                     continue
#                 if row['wkt_polygon'] == '':
#                     polygon = MultiPolygon()
#                 else:
#                     polygon = GEOSGeometry(row['wkt_polygon'])

#                 delivery_zone, created = DeliveryZone.objects.get_or_create(
#                     city=row['город'],  # Укажите ваш город
#                     name=row['имя'],  # Укажите имя для зоны доставки
#                     polygon=polygon,
#                     is_promo=row['promo'],  # Укажите значение промо
#                     promo_min_order_amount=row['мин заказ'],  # Укажите минимальную сумму заказа для промо
#                     delivery_cost=row['стоимость доставки'],  # Укажите стоимость доставки
#                 )
#                 if created:
#                     print(f"Delivery zone '{delivery_zone.name}' created")

#         self.stdout.write(
#             self.style.SUCCESS(
#                 'Load_delivery_zones executed successfully.'
#             )
#         )

class Command(BaseCommand):
    help = "Loads data from delivery_zones.csv"

    def handle(self, *args, **options):
        with open('docs/delivery_zones.csv', encoding='utf-8-sig') as f:
            combined_polygon = MultiPolygon()

            for row in DictReader(f, delimiter=';'):
                if not any(row.values()):
                    continue
                if row['wkt_polygon'] == '':
                    polygon = MultiPolygon()
                else:
                    # Преобразование строки координат в формат WKT
                    coordinates = row['wkt_polygon']
                    wkt_polygon = f"MULTIPOLYGON((({coordinates})))"
                    polygon = GEOSGeometry(wkt_polygon)

                if row['имя'] == 'zone3-1':
                    if not combined_polygon.empty:
                        polygon_minus = polygon.difference(combined_polygon)
                        polygon = polygon_minus

                else:
                    combined_polygon = combined_polygon.union(polygon)

                delivery_zone, created = DeliveryZone.objects.get_or_create(
                    city=row['город'],  # Укажите ваш город
                    name=row['имя'],  # Укажите имя для зоны доставки
                    polygon=polygon,
                    is_promo=row['promo'],  # Укажите значение промо
                    promo_min_order_amount=row['мин заказ'],  # Укажите минимальную сумму заказа для промо
                    delivery_cost=row['стоимость доставки'],  # Укажите стоимость доставки
                )
                if created:
                    print(f"Delivery zone '{delivery_zone.name}' created")

        self.stdout.write(
            self.style.SUCCESS(
                'Load_delivery_zones executed successfully.'
            )
        )

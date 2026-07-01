from __future__ import annotations

import re

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.db.utils import IntegrityError
from django.conf import settings

from catalog.models import Dish, DishCityPrice, DishPartnerPrice


class Command(BaseCommand):
    help = "Заполняет городские цены сайта и партнерские цены из старых полей Dish"

    def handle(self, *args, **options):
        cities = [city[0] for city in settings.CITY_CHOICES]
        partner_categories = [cat[0] for cat in settings.PARTNERS_PRICE_CATEGORIES]

        self.stdout.write("\n=== Заполнение цен блюд ===")

        city_prices = []
        partner_prices = []

        for dish in Dish.objects.iterator():
            for city in cities:
                city_prices.append(
                    DishCityPrice(
                        dish=dish,
                        city=city,
                        price=dish.price,
                        discount=dish.discount,
                        final_price=dish.final_price,
                    )
                )

                for partner_category in partner_categories:
                    if partner_category == "P1":
                        final_price = dish.final_price_p1
                    elif partner_category == "P2":
                        final_price = dish.final_price_p2
                    else:
                        continue

                    partner_prices.append(
                        DishPartnerPrice(
                            dish=dish,
                            city=city,
                            partner_category=partner_category,
                            final_price=final_price,
                        )
                    )

        with transaction.atomic():
            DishCityPrice.objects.bulk_create(
                city_prices,
                ignore_conflicts=True,
            )
            DishPartnerPrice.objects.bulk_create(
                partner_prices,
                ignore_conflicts=True,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✔ Создано/пропущено: "
                f"{len(city_prices)} городских цен, "
                f"{len(partner_prices)} партнерских цен."
            )
        )

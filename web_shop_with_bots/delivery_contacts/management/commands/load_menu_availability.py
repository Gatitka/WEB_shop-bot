import os
from datetime import time
from django.core.management import BaseCommand
from django.conf import settings

from delivery_contacts.models import Restaurant
from catalog.models import CityDishList, RestaurantDishList, Dish


class Command(BaseCommand):
    help = "Loads menu availability in cities and restaurants."

    def handle(self, *args, **options):
        dishes = Dish.objects.all()
        city_codes = [c[1] for c in settings.CITY_CHOICES]
        restaurants = Restaurant.objects.all()

        for city in city_codes:
            city_dish_list, created = CityDishList.objects.get_or_create(
                city=city,
            )
            for dish in dishes:
                city_dish_list.dish.add(dish)

        for restaurant in restaurants:
            rest_dish_list, created = RestaurantDishList.objects.get_or_create(
                restaurant=restaurant,
            )
            for dish in dishes:
                rest_dish_list.dish.add(dish)

        self.stdout.write(
            self.style.SUCCESS(
                'Loads menu availability in cities and restaurants.'
            )
        )

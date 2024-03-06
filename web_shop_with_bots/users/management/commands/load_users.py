from django.core.management import BaseCommand
from django.core.management import call_command
from users.models import UserAddress
import os
from django.contrib.auth import get_user_model


User = get_user_model()


class Command(BaseCommand):
    help = "Loads all TEST users"

    def handle(self, *args, **options):

        admin, created = User.objects.get_or_create(
            email="a@a.ru",
            is_active=True,
            is_superuser=True,
            is_staff=1,
            first_name='admin',
            last_name='admin',
            phone='+79055969166',
            web_language='ru',
        )
        admin.set_password("adminadmin0")
        admin.save()

        user1, created = User.objects.get_or_create(
            email="a1@a1.ru",
            first_name='Петя',
            last_name='Петин',
            phone='+79055969160',
            web_language='en',
        )
        user1.set_password("foreverlove0")
        user1.save()

        user2, created = User.objects.get_or_create(
            email="a2@a2.ru",
            first_name='Вася',
            last_name='Васин',
            phone='+79055969161',
            web_language='sr-latn'
        )
        user2.set_password("foreverlove0")
        user2.save()

        user3, created = User.objects.get_or_create(
            email="a3@a3.ru",
            first_name='Коля',
            last_name='Колин',
            phone='+79055969162'
        )
        user3.set_password("foreverlove0")
        user3.save()

        address1, created = UserAddress.objects.get_or_create(
            base_profile=user1.base_profile,
            address="Белград, ул.Милована Миловановича 1",
        )
        address2, created = UserAddress.objects.get_or_create(
            base_profile=user1.base_profile,
            address="Belgrade, ул.Милована Миловановича 2",
        )
        address3, created = UserAddress.objects.get_or_create(
            base_profile=user2.base_profile,
            address="Belgrade, ул.Милована Миловановича 3",
        )
        address4, created = UserAddress.objects.get_or_create(
            base_profile=user2.base_profile,
            address="Белград, ул.Милована Миловановича 4",
        )

        self.stdout.write(
            self.style.SUCCESS(
                'Load_users executed successfully.'
            )
        )

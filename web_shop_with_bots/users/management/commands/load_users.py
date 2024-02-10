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
            phone='+79055969166',
            language='ru',
        )
        admin.set_password("admin")
        admin.save()

        user1, created = User.objects.get_or_create(
            email="a1@a1.ru",
            first_name='Петя',
            phone='+79055969160',
            language='en',
        )
        user1.set_password("foreverlove")
        user1.save()

        user2, created = User.objects.get_or_create(
            email="a2@a2.ru",
            first_name='Вася',
            phone='+79055969161',
            language='sr-latn'
        )
        user2.set_password("foreverlove")
        user2.save()

        user3, created = User.objects.get_or_create(
            email="a3@a3.ru",
            first_name='Коля',
            phone='+79055969162'
        )
        user3.set_password("foreverlove")
        user3.save()

        address1, created = UserAddress.objects.get_or_create(
            base_profile=user1.base_profile,
            short_name="адрес1",
            city='Belgrade',
            full_address="ул.Милована Миловановича 1",
        )
        address2, created = UserAddress.objects.get_or_create(
            base_profile=user1.base_profile,
            short_name="адрес2",
            city='Belgrade',
            full_address="ул.Милована Миловановича 2",
        )
        address3, created = UserAddress.objects.get_or_create(
            base_profile=user2.base_profile,
            short_name="адрес3",
            city='Belgrade',
            full_address="ул.Милована Миловановича 3",
        )
        address4, created = UserAddress.objects.get_or_create(
            base_profile=user2.base_profile,
            short_name="адрес4",
            city='Belgrade',
            full_address="ул.Милована Миловановича 4",
        )

        self.stdout.write(
            self.style.SUCCESS(
                'Load_users executed successfully.'
            )
        )

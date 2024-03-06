from django.core.management import BaseCommand
from django.core.management import call_command
from delivery_contacts.models import Delivery, Restaurant
import os


class Command(BaseCommand):
    help = "Loads all delivery_data"

    def handle(self, *args, **options):
        call_command('load_delivery_zones')

        shop1, created = Restaurant.objects.get_or_create(
            short_name='центр',
            address='Milovana Milovanovića 4',
            open_time="9:00",
            close_time="22:00",
            phone="+381 61 271 4798",
            city='Beograd',
            is_active=True,
            is_default=True,
            image=os.path.join('contacts', 'shop1.jpg')
        )
        shop2, created = Restaurant.objects.get_or_create(
            short_name='центр2',
            address='Štark arena',
            open_time="9:00",
            close_time="22:00",
            phone="+381 11 222 3333",
            city='Beograd',
            is_active=True,
            image=os.path.join('contacts', 'shop2.jpg')
        )

        delivery1, created = Delivery.objects.get_or_create(
            type='delivery',
            city='Beograd',
            is_active=True,
            image=os.path.join('contacts', 'delivery1.jpg'),
        )
        delivery1.set_current_language('ru')
        delivery1.description = (
            "Бесплатная доставка\n"
            "Стари Град, Дорчол, Врачар, Белград на Води - заказы от 2500 дин.\n"
            "Другие районы уточняйте у администратора."
            )
        delivery1.save()
        delivery1.set_current_language('en')
        delivery1.description = (
            "Free delivery\n"
            "Stari Grad, Dorchol, Vrachar, Begrade na vodi for orders from 2500 din.\n"
            "Ask our operator for other districts."
            )
        delivery1.save()
        delivery1.set_current_language('sr-latn')       # Only switches
        delivery1.description = (
            "Besplatna dostava\n"
            "Stari Grad, Dorćol, Vračar, Beograd na vodi - porudžbine od 2500 din.\n"
            "Za druge opštine obratite se administratoru. "
            )
        delivery1.save()

        delivery2, created = Delivery.objects.get_or_create(
            type='takeaway',
            city='Beograd',
            discount='10.00',
            is_active=True,
        )
        delivery2.set_current_language('ru')
        delivery2.description = 'Скидка при самовывозе 10%.'
        delivery2.save()
        delivery2.set_current_language('en')
        delivery2.description = 'Discount for takeaway 10%.'
        delivery2.save()
        delivery2.set_current_language('sr-latn')       # Only switches
        delivery2.description = 'Za samostalno preuzimanje popust od 10%.'
        delivery2.save()

        self.stdout.write(
            self.style.SUCCESS(
                'Load_delivery_data executed successfully.'
            )
        )

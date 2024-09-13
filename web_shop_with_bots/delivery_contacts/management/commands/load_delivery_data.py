import os
from datetime import time
from django.core.management import BaseCommand, call_command

from delivery_contacts.models import Delivery, Restaurant


class Command(BaseCommand):
    help = "Loads all delivery_data"

    def handle(self, *args, **options):
        call_command('load_delivery_zones')

        shop1, created = Restaurant.objects.get_or_create(
            short_name='центр',
            address='Milovana Milovanovića 4',
            open_time="11:00",
            close_time="22:00",
            phone="+381 61 271 4798",
            city='Beograd',
            is_active=True,
            is_default=True,
            image=os.path.join('contacts', 'shop1.jpg')
        )

        shop2, created = Restaurant.objects.get_or_create(
            short_name='Н1',
            address='Hajduk Veljkova 11',
            open_time="11:00",
            close_time="22:00",
            phone="+381 61 271 4798",
            city='Novi Sad',
            is_active=True,
            is_default=True,
            image=None
        )

        delivery1, delivery1_created = Delivery.objects.get_or_create(
            type='delivery',
            city='Beograd',
            is_active=True,
            min_time=time(11, 30),
            max_time=time(22, 00),
            image=os.path.join('contacts', 'delivery1.jpg'),

        )
        if delivery1_created:
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

        delivery2, delivery2_created = Delivery.objects.get_or_create(
            type='takeaway',
            city='Beograd',
            discount='10.00',
            is_active=True,
            min_time=time(11, 0),
            max_time=time(22, 0),
        )
        if delivery2_created:
            delivery2.set_current_language('ru')
            delivery2.description = 'Скидка при самовывозе 10%.'
            delivery2.save()
            delivery2.set_current_language('en')
            delivery2.description = 'Discount for takeaway 10%.'
            delivery2.save()
            delivery2.set_current_language('sr-latn')       # Only switches
            delivery2.description = 'Za samostalno preuzimanje popust od 10%.'
            delivery2.save()

        delivery3, delivery3_created = Delivery.objects.get_or_create(
            type='delivery',
            city='Novi Sad',
            is_active=True,
            image=None,
            min_time=time(11, 30),
            max_time=time(22, 00),
        )
        if delivery3_created:
            delivery3.set_current_language('ru')
            delivery3.description = (
                "Бесплатная доставка \n"
                "- заказы от 2500 дин.\n"
                "Другие районы уточняйте у администратора."
                )
            delivery3.save()
            delivery3.set_current_language('en')
            delivery3.description = (
                "Free delivery \n"
                "for orders from 2500 din.\n"
                "Ask our operator for other districts."
                )
            delivery3.save()
            delivery3.set_current_language('sr-latn')       # Only switches
            delivery3.description = (
                "Besplatna dostava \n"
                "- porudžbine od 2500 din.\n"
                "Za druge opštine obratite se administratoru. "
                )
            delivery3.save()

        delivery4, delivery4_created = Delivery.objects.get_or_create(
            type='takeaway',
            city='Novi Sad',
            discount='10.00',
            is_active=True,
            min_time=time(11, 0),
            max_time=time(22, 0),
        )
        if delivery4_created:
            delivery4.set_current_language('ru')
            delivery4.description = 'Скидка при самовывозе 10%.'
            delivery4.save()
            delivery4.set_current_language('en')
            delivery4.description = 'Discount for takeaway 10%.'
            delivery4.save()
            delivery4.set_current_language('sr-latn')       # Only switches
            delivery4.description = 'Za samostalno preuzimanje popust od 10%.'
            delivery4.save()

        self.stdout.write(
            self.style.SUCCESS(
                'Load_delivery_data executed successfully.'
            )
        )

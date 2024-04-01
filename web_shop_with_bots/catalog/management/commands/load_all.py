from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Loads all test data"

    def handle(self, *args, **options):
        call_command('load_menu')
        call_command('load_delivery_data')
        call_command('load_promo')
        call_command('load_users')

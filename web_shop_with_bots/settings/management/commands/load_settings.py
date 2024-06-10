from django.core.management import BaseCommand
from datetime import time

from settings.models import OnlineSettings


class Command(BaseCommand):
    help = "Loads settings."

    def handle(self, *args, **options):

        settings, _ = OnlineSettings.objects.get_or_create(
            name='общие',
            is_active=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                'Load_settings executed successfully.'
            )
        )

from csv import DictReader

from django.core.management import BaseCommand
from django.conf import settings
from tm_bot.models import AdminChatTM


class Command(BaseCommand):
    help = "Loads test admin chat in Tm from .env"

    def handle(self, *args, **options):
        admin_chat_bg, _ = AdminChatTM.objects.get_or_create(
            city='Beograd',
            chat_id=settings.CHAT_ID1,
            restaurant_id=1,
            )

        admin_chat_ns, _ = AdminChatTM.objects.get_or_create(
            city='NoviSad',
            chat_id=settings.CHAT_ID2,
            restaurant_id=2,
            )

        self.stdout.write(
            self.style.SUCCESS(
                'Load test admin chats executed successfully.'
            )
        )

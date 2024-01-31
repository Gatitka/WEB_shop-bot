import asyncio
import logging
import sys

from django.core.management import BaseCommand

from ...handlers import other
from .bot import bot, dp


class Command(BaseCommand):
    help = "Запуск Телеграм-бота"

    def handle(self, *args, **options):

        other.register_handlers_other(dp)

        async def main() -> None:
            await dp.start_polling(bot, skip_updates=True)

        #if __name__ == "__main__":
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)
        asyncio.run(main())

from ...handlers import other

import sys
import logging
import asyncio
from .bot import dp, bot
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "Запуск Телеграм-бота"

    def handle(self, *args, **options):

        other.register_handlers_other(dp)

        async def main() -> None:
            await dp.start_polling(bot, skip_updates=True)

        #if __name__ == "__main__":
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)
        asyncio.run(main())

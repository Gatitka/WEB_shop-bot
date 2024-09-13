import asyncio
import logging
import sys

from django.core.management import BaseCommand
from tm_bot.handlers import status
from tm_bot.admin_bot import bot, dp


class Command(BaseCommand):
    help = "Запуск Админ Телеграм-бота"

    def handle(self, *args, **options):
        # Регистрация обработчиков
        status.register_handlers_status(dp)
        status.register_handlers_common(dp)

        async def main() -> None:
            await dp.start_polling(bot, skip_updates=True)

        # if __name__ == "__main__":
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)
        asyncio.run(main())

import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )
    )
)

load_dotenv(os.path.join(os.path.dirname(BASE_DIR), 'infra', '.env'),
            verbose=True)

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    exit("No token provided")

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=storage)

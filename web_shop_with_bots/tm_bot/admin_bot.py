from aiogram import Bot, Dispatcher
from django.conf import settings
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_shop_with_bots.settings')


bot = Bot(token=settings.ADMIN_BOT_TOKEN, parse_mode="MarkdownV2")
dp = Dispatcher()

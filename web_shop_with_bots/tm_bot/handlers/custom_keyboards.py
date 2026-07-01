from django.conf import settings
from aiogram import types
import tm_bot.handlers.keyboards as bot_kb


def get_inline_keyboard(broadcast):
    """Возвращаем инлайн кнопку с переходом на миниапп. (под сообщением)"""
    city = broadcast.city  # свойство в модели, см. PromoBroadcast.city
    base_url = f"{settings.PROTOCOL}://{settings.DOMAIN}"
    if not base_url or not city:
        return None

    campaign = {"Beograd": "NfxTGmp5R8",
                "NoviSad": "K6x4qdQAOG"}
    # например: https://mini.yumesushi.rs/?city=Beograd
    miniapp_url = f"{base_url}?city={city}&start={campaign.get(city)}"
    print(f"----------------------------------> {miniapp_url}")
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Открыть меню MINI-APP🍣",
                    web_app=types.WebAppInfo(url=miniapp_url),
                    # если хочется просто ссылку в браузер:
                    # url=miniapp_url
                )
            ]
        ]
    )
    return keyboard


def get_reply_keyboard(broadcast):
    """ Возвращаем стандартную реплай панель бота в нижней части экрана."""
    return bot_kb.get_commands_kb()

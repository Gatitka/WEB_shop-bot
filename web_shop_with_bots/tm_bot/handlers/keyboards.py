from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           ReplyKeyboardMarkup, WebAppInfo,
                           KeyboardButton)


# START keyboard
def get_start_kb(webapp_url: str) -> InlineKeyboardMarkup:
    # Одна большая кнопка, открывающая WebApp
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🍣 Открыть меню",
                                  web_app=WebAppInfo(url=webapp_url))]
        ]
    )


def get_commands_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="⚙️ Уведомления")],
            [KeyboardButton(text="🔁 В начало")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_support_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Позвонить"), KeyboardButton(text="✉️ Написать")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_subscription_settings() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔕 Выключить"), KeyboardButton(text="🔔 Включить")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

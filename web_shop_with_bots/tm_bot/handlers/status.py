from aiogram import Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from ..admin_bot import bot
from shop.models import Order
from django.conf import settings
from asgiref.sync import sync_to_async


CHAT_ID = settings.CHAT_ID


async def cmd_start(message: types.Message):
    if message.chat.type == "private":
        await message.answer("Привет! Я бот. Чтобы начать, напиши /help.")
    elif message.chat.type in ["group", "supergroup"]:
        await message.reply("Привет всем! Я бот. Чтобы начать, напишите /help.")


async def cmd_help(message: types.Message):
    await message.reply("Это помощь.")


async def send_new_order_notification(order_id: int, order_status: str, text: str):
    # keyboard = types.InlineKeyboardMarkup()
    # keyboard.add(types.InlineKeyboardButton(
    #     "🔄 Изменить статус",
    #     callback_data=f"change_status_{order_id}"))

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="🔄 Изменить статус",
                    callback_data=f"change_status_{order_id}",
                    url=''
                )
            ]
        ]
    )

    message = await bot.send_message(
        chat_id=CHAT_ID, text=text,
        reply_markup=keyboard)

    await sync_to_async(Order.objects.filter(id=order_id).update)(admin_tm_msg_id=message.message_id)


async def change_status_callback(query: types.CallbackQuery):
    order_id = int(query.data.split('_')[2])

    order_status_choices = [
        ("WCO", "ожидает подтверждения"),
        ("CFD", "подтвержден"),
        ("OND", "передан в доставку"),
        ("CND", "отменен"),
        ("DLD", "выдан")
    ]

    keyboard = types.InlineKeyboardMarkup()
    for status_code, status_text in order_status_choices:
        keyboard.add(types.InlineKeyboardButton(
            status_text,
            callback_data=f"set_status_{order_id}_{status_code}"))

    keyboard.add(types.InlineKeyboardButton(
        "Назад",
        callback_data="back_to_main_menu"))

    await query.message.edit_text(f"▶️ {query.message.text}",
                                  reply_markup=keyboard)


async def set_status_callback(query: types.CallbackQuery):
    order_id = int(query.data.split('_')[2])
    new_status = query.data.split('_')[3]

    Order.objects.filter(id=order_id).update(status=new_status)

    await query.answer(f"Статус заказа изменен на {new_status}")
    await query.message.edit_text(f"▶️ {new_status}")


def register_handlers_status(dp: Dispatcher):
    dp.callback_query.register(
        change_status_callback,
        lambda query: query.data.startswith("change_status_"))
    dp.callback_query.register(
        set_status_callback,
        lambda query: query.data.startswith("set_status_"))


def register_handlers_common(dp: Dispatcher):
    dp.message.register(cmd_start, Command(commands=['start']))
    dp.message.register(cmd_help, Command(commands=['help']))

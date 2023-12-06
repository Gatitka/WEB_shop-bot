from aiogram import Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hbold

from users.models import User
from tm_bot.models import Message


# @dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    chat_id = message.from_user.id
    text = message.text
    u, _ = User.objects.get_or_create(
        Tm_ID=chat_id,
        defaults={
            'Tm_username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name
        }
    )

    await message.answer(f"Hello, {hbold(message.from_user.full_name)}!")


# @dp.message_handler(commands='menu')
async def menu(message: types.Message):
    await message.answer(
        "Выбери команду для следующего действия:\n"
        + "💸/add_expence - добавить затраты\n"
        + "📉/report - увидеть отчет"
        + "/start - вернуться в основное меню",
        reply_markup=kb.get_menu_kb()
    )
    await message.delete()


# @dp.callback_query_handler(text='cancel', state='*')
async def cancel(call: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await call.message.delete()
        return
    await state.finish()
    await call.answer("Запись отменена.")
    await call.message.delete()


# @dp.message()
async def echo_handler(message: types.Message) -> None:
    """
    Handler will forward receive a message back to the sender
    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    try:
        # Send a copy of the received message
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        # But not all the types is supported to be copied so need to handle it
        await message.answer("Nice try!")


def register_handlers_other(dp: Dispatcher):
    dp.message.register(command_start_handler)
    dp.message.register(echo_handler)
    dp.message.register(menu, command=['menu'])
    dp.register_callback_query_handler(cancel, text='cancel', state='*')

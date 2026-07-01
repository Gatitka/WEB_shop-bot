from aiogram import types
from django.conf import settings

from django.utils import timezone
from exceptions import BotMessageSendError
import requests
from typing import Optional, Union, Dict, Any, List

from tm_bot.models import (OrdersBot, AdminChatTM, MessengerAccount,
                           MessengerAccountBot)
import tm_bot.text_assemble_and_edition as ta
import tm_bot.handlers.custom_keyboards as custom_kb
from django.db import close_old_connections
from django.db.utils import InterfaceError, OperationalError


import logging

logger = logging.getLogger(__name__)


KeyboardType = Union[types.ReplyKeyboardMarkup, types.InlineKeyboardMarkup]

# ----------------------------   HELPERS ---------------------------------
def get_chat_id_by_order(order):
    admin_chat = AdminChatTM.objects.filter(
                                    restaurant=order.restaurant).first()
    if admin_chat:
        return admin_chat.chat_id
    else:
        return settings.CHAT_ID


def get_admin_chat_id_by_city(city):
    admin_chat = AdminChatTM.objects.filter(city=city).first()
    if admin_chat:
        return admin_chat.chat_id
    else:
        return settings.CHAT_ID


def get_chat_id_by_bot(bot):
    admin_chat = AdminChatTM.objects.filter(
                                    city=bot.city).first()
    if admin_chat:
        return admin_chat.chat_id
    else:
        return settings.CHAT_ID


def get_bot_id_by_city(city):
    bot = OrdersBot.objects.filter(city=city).first()
    if not bot:
        logger.warning(
                "No OrdersBot found for city=%s", city
            )
        return [None, None]
    #     if bot.api_key is not None and not api_key_is_valid(bot, data):
    #         return ValidationError("API key isn't correct")

    return [bot, bot.id]


def get_client_messenger_account_by_order(order):
    messenger_account = None
    if order.user and order.user.messenger_account:
        if order.user.messenger_account:
            messenger_account = order.user.messenger_account
    elif order.msngr_account:
        messenger_account = order.messenger_account

    if messenger_account and messenger_account.msngr_type == 'tm':
        return messenger_account

    logger.debug(f"Order {order} has no 'user' or 'messenger_account'.")
    return None


def get_candidate_bots_for_user(
    messenger_account: MessengerAccount,
    order_city: Optional[str] = None,
) -> list[OrdersBot]:
    """
    Возвращает список ботов-кандидатов для отправки сообщения пользователю.

    1) Сначала бот города заказа (если передан order_city).
    2) Затем бот основного города клиента (messenger_account.city),
       если он отличается от города заказа.
    """
    candidates: list[OrdersBot] = []

    # 1. Бот города заказа
    if order_city:
        try:
            bot_order_city = OrdersBot.objects.get(city=order_city)
            candidates.append(bot_order_city)
        except OrdersBot.DoesNotExist:
            logger.warning(
                "No OrdersBot found for order_city=%s", order_city
            )

    # 2. Бот основного города клиента
    user_city = messenger_account.city
    if user_city and user_city != order_city:
        try:
            bot_user_city = OrdersBot.objects.get(city=user_city)
            candidates.append(bot_user_city)
        except OrdersBot.DoesNotExist:
            logger.warning(
                "No OrdersBot found for user_city=%s", user_city
            )

    # Убираем возможные дубликаты, если города совпали
    unique_candidates: list[OrdersBot] = []
    seen_ids = set()
    for bot in candidates:
        if bot.id not in seen_ids:
            unique_candidates.append(bot)
            seen_ids.add(bot.id)
    logger.debug("Candidate Bots: %s", unique_candidates)
    return unique_candidates


def build_keyboard_for_broadcast(broadcast):
    """ Строит клавиатуру к сообщению."""
    if not broadcast.add_inline_keyboard and not broadcast.add_reply_keyboard:
        return None

    if broadcast.add_inline_keyboard:
        return custom_kb.get_inline_keyboard(broadcast)
    elif broadcast.add_reply_keyboard:
        return custom_kb.get_reply_keyboard(broadcast)


def classify_telegram_response(data: dict) -> tuple[str, str | None]:
    """
    Возвращает:
    - internal status
    - db error code
    """
    if not data:
        return "unknown error", "empty_response"

    if data.get("ok"):
        return "ok", None

    error_code = data.get("error_code")
    desc = (data.get("description") or "").lower()

    if error_code == 403 and "bot was blocked" in desc:
        return "bot was blocked", "403_bot_blocked"

    if error_code == 403 and "user is deactivated" in desc:
        return "user is deactivated", "403_user_deactivated"

    if error_code == 400 and "chat not found" in desc:
        return "chat not found", "400_chat_not_found"

    if error_code == 429:
        return "rate limited", "429_rate_limited"

    if error_code and int(error_code) >= 500:
        return "temporary error", f"{error_code}_telegram_server_error"

    return "error", f"{error_code}_unknown" if error_code else "unknown_error"


def update_mab_send_result(
    messenger_account: MessengerAccount,
    bot: OrdersBot,
    status: str,
    db_error_code: str | None = None,
) -> None:
    """ Единый хелпер для обновления MessengerAccountBot по результату рассылки."""
    try:
        mab, _ = MessengerAccountBot.objects.get_or_create(
            messenger_account=messenger_account,
            bot=bot,
        )
        now = timezone.now()

        if status == "ok":
            mab.tg_can_write = True
            mab.last_success_at = now
            mab.last_error_at = None
            mab.last_error_code = None
            mab.save(update_fields=[
                "tg_can_write",
                "last_success_at",
                "last_error_at",
                "last_error_code",
            ])
            return

        if status in {"bot was blocked", "chat not found", "user is deactivated"}:
            mab.tg_can_write = False
            mab.last_error_at = now
            mab.last_error_code = db_error_code
            mab.save(update_fields=[
                "tg_can_write",
                "last_error_at",
                "last_error_code",
            ])
            return

        # временные / непонятные ошибки: статус связи не меняем
        mab.last_error_at = now
        mab.last_error_code = db_error_code or status
        mab.save(update_fields=[
            "last_error_at",
            "last_error_code",
        ])

    except (InterfaceError, OperationalError) as e:
        logger.warning(
            "DB error while updating MessengerAccountBot for user=%s bot=%s: %s",
            messenger_account.id, bot.id, e
        )
# ---------------------------- UNITED SEND MESSAGES ---------------------------------

def send_message_new_order_admin_user(order):
    """ Отправка сообщения телеграм-ботом в:
        Админский чат о новом заказе. (последовательно)
        +
        Пользователю отправляем сначала в бот города.
        Если не получилось, то в его бот с пометкой, что вопросы по заказу к админу другого города"""
    send_message_new_order_to_admin(order)
    # send_message_new_order_to_user_other_city(order)


def send_messages_order_status_update_user_bot(new_status, order):
    """ Отправка сообщений телеграм-ботом
        Botobot для учета в их системе, если заказ из бота и
        settings.SEND_BOTOBOT_UPDATES = True.
        Ботобот сам уведомляет клиента о смене статуса.

        +

        Пользователю о смене статуса.
        """
    from tm_bot.tasks import send_order_status_update_task

    if order.source == '3':
        if settings.SEND_BOTOBOT_UPDATES:
            # отправить в botobot инфу об изменении статуса
            # он сам уведомляет клиента
            logger.info('Botobot status update trigered.\n'
                         'Order: %s', order)
            send_request_order_status_update(new_status,
                                             int(order.source_id),
                                             order.orders_bot)
        else:
            # Если ботобот отключен, то МЫ отправляем сообщение о смене статуса.
            # Мы не проверяем наличие order.user.messenger_account тут,
            # т.к. предполагается что заказ пришел из бота,
            # но в таске это проверяется еще раз все равно
            logger.info('Send status update task is trigered.\n'
                         'Order: %s', order)
            send_order_status_update_task.delay(new_status, order.id)

    elif order.source == '4':
        # Мы проверяем наличие order.user.messenger_account.msngr_type='tm',
        # т.к. user вообще может быть незарег, не тригерим холостую таску.
        ma = get_client_messenger_account_by_order(order)
        if ma:
            # отправить сообщение клиенту об изменении статуса
            send_order_status_update_task.delay(new_status, order.id)


# def send_messages_order_status_update_user(new_status, order):
#     """ Отправка сообщения телеграм-ботом в:
#         Пользователю о смене статуса.
#         +
#         Botobot для учета в их системе. (отпадет)
#         """

#     # отправить сообщение клиенту об изменении статуса
#     send_status_update_message_to_client(new_status, order)


# ---------------------------- TO ADMIN CHAT SEND MESSAGES ---------------------------------
# последоватлеьно шлем сообщение в админский чат без всяких fallback и пр

def send_message_new_order_to_admin(order):
    """ Отправка сообщения телеграм-ботом в админский чат
        о новом заказе."""

    message = ta.get_admin_message_new_order(order)
    cleaned_message = ta.escape_markdown(message)
    chat_id = get_chat_id_by_order(order)
    return send_message_telegram(chat_id,
                                 cleaned_message,
                                 settings.ADMIN_BOT_TOKEN,
                                 disable_link_preview=True)


def send_error_message_order_unsaved(bot, order_id, e):
    """ Отправка сообщения телеграм-ботом в админский чат
        о том, что заказ из бота не сохранился."""

    message = f'❗️Заказ TM BOT #{order_id} не сохранился в базе данных.'
    cleaned_message = ta.escape_markdown(message)
    chat_id = get_chat_id_by_bot(bot)
    send_message_telegram(chat_id, cleaned_message, settings.ADMIN_BOT_TOKEN)


def send_error_message_order_saved(order):
    """ Отправка сообщения телеграм-ботом в админский чат
        о том, что заказ из бота сохранился но с ошибками."""

    message = f'❗️Заказ TM BOT #{order.source_id} сохранился с ошибками или требует уточнения.'
    cleaned_message = ta.escape_markdown(message)
    chat_id = get_chat_id_by_order(order)
    send_message_telegram(chat_id, cleaned_message, settings.ADMIN_BOT_TOKEN)


def send_message_admin_changed_settings(message, city):
    """ Отправка сообщения телеграм-ботом в админский чат
        об изменениях в системе, сделанных админом."""

    cleaned_message = ta.escape_markdown(message)
    chat_id = get_admin_chat_id_by_city(city)
    return send_message_telegram(chat_id,
                                 cleaned_message,
                                 settings.ADMIN_BOT_TOKEN,
                                 disable_link_preview=True)

# ---------------------------- TO CLIENT SEND MESSAGES ---------------------------------


def send_message_new_order_to_user_other_city(order):
    """ Отправка сообщения телеграм-ботом в чат клиенту
        о новом заказе, если выбранный город."""
    # send_message_to_user_with_fallback
    pass


def send_status_update_message_to_client(status, order):
    """ Отправка сообщения телеграм-ботом клиенту
        о том, что заказ поменял статус."""
    logger.debug("Prepare tm as order %s changed status to %s.", order, status)
    ma = get_client_messenger_account_by_order(order)

    if ma:
        cleaned_message = ta.get_status_message(status)

        order_city = getattr(order, "city", None)

        logger.debug(
            "Sending status update to user %s for order %s (city=%s).",
            ma.id, order, order_city,
        )

        reply = send_message_to_user_with_fallback(
            messenger_account=ma,
            message=cleaned_message,
            order_city=order_city)
        return reply


def check_new_account_subscription(messenger_account: MessengerAccount
                                   ) -> bool | None:

    city = messenger_account.city
    text = ("Проверка связи! ✨\n"
            "Настраиваем привязку — скоро всё заработает.")
    bot = get_bot_id_by_city(city)[0]
    if not bot:
        return None

    bot_token = settings.TELEGRAM_AUTH_BOTS.get(bot.city)
    try:
        send_user_message_via_bot(messenger_account=messenger_account,
                                  bot=bot,
                                  message=ta.escape_markdown(text),
                                  bot_token=bot_token)

    except Exception:
        pass


def check_old_account_changed_subscription(messenger_account: MessengerAccount,
                                           ) -> None:

    bot = get_bot_id_by_city(messenger_account.city)[0]
    if not bot:
        return None

    text = "Внесены изменения в профиль 👓."
    bot_token = settings.TELEGRAM_AUTH_BOTS.get(bot.city)
    try:
        send_user_message_via_bot(messenger_account=messenger_account,
                                  bot=bot,
                                  message=ta.escape_markdown(text),
                                  bot_token=bot_token)

    except Exception:
        pass


def check_telegram_subscription(bot_token: str,
                                user_id: str,
                                text: str) -> bool | None:
    """
    Пробуем отправить тестовое сообщение.
    True  -> можно писать
    False -> пользователь запретил / заблокировал
    None  -> другая ошибка (сетевые проблемы и т.п.)
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": user_id,
        "text": text
    })
    try:
        data = resp.json()
    except Exception:
        return None

    status, _ = classify_telegram_response(data)

    if status == "ok":
        return True

    if status in {"bot was blocked", "chat not found", "user is deactivated"}:
        return False

    return None

# ---------------------------- BASE METHODS ---------------------------------


def send_message_to_user_with_fallback(
        messenger_account: MessengerAccount,
        message: str,
        *,
        order_city: Optional[str] = None,
        keyboard: Optional[KeyboardType] = None,
        disable_link_preview: bool = False,
        parse_mode: str = "MarkdownV2",
    ) -> Optional[dict]:
    """
    Отправить сообщение пользователю с учётом:
    - технического состояния per-бот (MessengerAccountBot),
    - приоритета: сначала бот города заказа/миниапки,
        затем бот основного города клиента.

    Возвращает data успешной отправки или None, если никем не смогли доставить.
    В случае сетевых/критических ошибок может выбросить BotMessageSendError.
    """

    # 1. Формируем список кандидатов-ботов
    candidate_bots = get_candidate_bots_for_user(
        messenger_account=messenger_account,
        order_city=order_city,
    )

    if not candidate_bots:
        logger.warning(
            "No candidate bots found for messenger_account=%s, "
            "order_city=%s.",
            messenger_account.id,
            order_city,
        )
        return None

    last_error: Optional[Exception] = None

    # 2. Перебираем ботов-кандидатов
    for bot in candidate_bots:
        # Проверяем состояние tg_can_write, если есть
        mab = MessengerAccountBot.objects.filter(
            messenger_account=messenger_account,
            bot=bot,
        ).first()

        if mab and mab.tg_can_write is False:
            # Уже знаем, что этот бот заблокирован — не пробуем ещё раз
            logger.info(
                "Skip bot %s for user %s: tg_can_write is False.",
                bot.id,
                messenger_account.id,
            )
            continue

        # Получаем токен бота (как у тебя настроено — тут пример)
        bot_token = settings.TELEGRAM_AUTH_BOTS.get(bot.city)
        if not bot_token:
            logger.error(
                "No bot token configured for bot %s (city=%s).",
                bot.id,
                bot.city,
            )
            continue

        try:
            status, data = send_user_message_via_bot(
                messenger_account=messenger_account,
                bot=bot,
                message=message,
                bot_token=bot_token,
                keyboard=keyboard,
                disable_link_preview=disable_link_preview,
                parse_mode=parse_mode,
            )
        except BotMessageSendError as exc:
            # Считаем это временной/общей ошибкой, пробуем других ботов
            logger.exception(
                "Error sending message to user %s via bot %s: %s",
                messenger_account.id,
                bot.id,
                exc,
            )
            last_error = exc
            continue

        if status == "ok":
            return data

        if status in {
            "bot was blocked",
            "chat not found",
            "user is deactivated",
            "invalid chat",
        }:
            continue

        # На всякий случай: если вернулся какой-то другой статус
        logger.warning(
            "Unexpected status '%s' from send_user_message_via_bot "
            "for user %s via bot %s.",
            status,
            messenger_account.id,
            bot.id,
        )

    # Если дошли сюда — никто не смог отправить
    if last_error:
        # По желанию можно либо пробрасывать, либо тихо логировать.
        logger.warning(
            "Failed to deliver message to user %s via all candidate bots.",
            messenger_account.id,
        )
    return None


def send_user_message_via_bot(
    messenger_account: MessengerAccount,
    bot: OrdersBot,
    message: str,
    bot_token: str,
    keyboard: Optional[KeyboardType] = None,
    disable_link_preview: bool = False,
    parse_mode: str = "MarkdownV2",
) -> tuple[str, dict]:
    """
    Отправка сообщения пользователю через конкретного OrdersBot
    с обновлением связки MessengerAccountBot.

    Возвращает (status, data), где status:
      - "ok"
      - "bot was blocked"
      - "error" (для других ошибок Telegram/сети, если не будет исключения)
    """
    chat_id = messenger_account.tm_chat_id or messenger_account.msngr_id
    if not chat_id:
        update_mab_send_result(
            messenger_account=messenger_account,
            bot=bot,
            status="invalid chat",
            db_error_code="no_chat_id",
        )
        return "invalid chat", {"detail": "no chat_id"}

    status, data = send_message_telegram(
        chat_id=chat_id,
        message=message,
        bot_token=bot_token,
        keyboard=keyboard,
        disable_link_preview=disable_link_preview,
        parse_mode=parse_mode,
    )

    _, db_error_code = classify_telegram_response(data)
    update_mab_send_result(
        messenger_account=messenger_account,
        bot=bot,
        status=status,
        db_error_code=db_error_code,
    )

    if status == "ok":
        logger.info("Message sent to user %s via bot %s successfully.", chat_id, bot.id)
    elif status == "bot was blocked":
        logger.info("User %s blocked bot %s.", chat_id, bot.id)
    elif status == "chat not found":
        logger.info("User %s never started bot %s (chat not found).", chat_id, bot.id)
    elif status == "user is deactivated":
        logger.info("User %s is deactivated for bot %s.", chat_id, bot.id)
    else:
        logger.warning(
            "Unexpected telegram status '%s' for user %s via bot %s. data=%s",
            status, chat_id, bot.id, data
        )

    return status, data


def send_user_photo_via_bot(
    bot_token: str,
    messenger_account: MessengerAccount = None,
    bot: OrdersBot = None,
    test_chat_id: str = None,
    photo_url: str = None,
    caption: Optional[str] = None,
    disable_link_preview: bool = False,
    parse_mode: Optional[str] = None,
    keyboard: Optional[KeyboardType] = None,
) -> tuple[str, dict]:
    """
    Отправка фото пользователю через конкретного OrdersBot.

    Возвращает (status, data), где status может быть:
      - "ok"
      - "bot was blocked"
      - "chat not found"
      - "user is deactivated"
      - "invalid chat"
      - "rate limited"
      - "temporary error"
      - "error"
    """
    # 1. Определяем chat_id
    if messenger_account:
        chat_id = messenger_account.tm_chat_id or messenger_account.msngr_id
        if not chat_id:
            update_mab_send_result(
                messenger_account=messenger_account,
                bot=bot,
                status="invalid chat",
                db_error_code="no_chat_id",
            )
            return "invalid chat", {"detail": "no chat_id"}
    else:
        if not test_chat_id:
            return "invalid chat", {"detail": "no chat_id"}
        chat_id = test_chat_id

    # 2. Собираем payload
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

    payload: dict = {
        "chat_id": chat_id,
        "photo": photo_url,
    }
    if caption:
        payload["caption"] = caption
    if parse_mode and caption:
        payload["parse_mode"] = parse_mode
    if disable_link_preview:
        # для caption Telegram тоже умеет выключать превью
        payload["disable_web_page_preview"] = True
    if keyboard:
        payload["reply_markup"] = keyboard.model_dump(mode="json")

    # 3. Отправляем запрос
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        status, db_error_code = classify_telegram_response(data)

    except Exception as e:
        status = "temporary error"
        db_error_code = "request_exception"
        data = {"exception": str(e)}
        logger.exception(
            "Error while sending photo to user %s via bot %s",
            chat_id,
            getattr(bot, "id", None),
        )

    # 4. Обновляем MessengerAccountBot, если это не тестовая отправка
    if messenger_account and bot:
        update_mab_send_result(
            messenger_account=messenger_account,
            bot=bot,
            status=status,
            db_error_code=db_error_code,
        )

    # 5. Пишем понятные логи
    if status == "ok":
        logger.info(
            "Photo sent to user %s via bot %s successfully.",
            chat_id,
            getattr(bot, "id", None),
        )
    elif status == "bot was blocked":
        logger.info(
            "User %s blocked bot %s (photo send).",
            chat_id,
            getattr(bot, "id", None),
        )
    elif status == "chat not found":
        logger.info(
            "User %s never started bot %s (chat not found, photo send).",
            chat_id,
            getattr(bot, "id", None),
        )
    elif status == "user is deactivated":
        logger.info(
            "User %s is deactivated for bot %s (photo send).",
            chat_id,
            getattr(bot, "id", None),
        )
    else:
        logger.warning(
            "Unexpected telegram photo send status '%s' for user %s via bot %s. data=%s",
            status,
            chat_id,
            getattr(bot, "id", None),
            data,
        )

    return status, data


def send_message_telegram(chat_id, message, bot_token,
                          keyboard: Optional[KeyboardType] = None,
                          disable_link_preview: bool = False,
                          parse_mode: str = "MarkdownV2"):
    """ Базовая функция для отправки сообщения в телеграм."""

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_link_preview,
    }
    if keyboard:
        dumped = keyboard.model_dump(mode="json", exclude_unset=True, exclude_none=True)
        #import json
        #logger.debug("Keyboard JSON: %s", json.dumps(dumped, ensure_ascii=False, indent=2))
        payload["reply_markup"] = dumped
    logger.info("Sending telegram message to %s", chat_id)
    try:
        response = requests.post(
                url,
                json=payload,
                timeout=(5, 30),
            )
        data = response.json()
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        raise BotMessageSendError(f"Telegram request failed: {e}")

    status, _ = classify_telegram_response(data)
    return status, data

# ---------------------------- BOTOBOT ---------------------------------

def send_request_order_status_update(new_status, order_id, bot):
    """ Функция для отправки уведомления в botobot о смене статуса у заказа."""
    # token = settings.BOTOBOT_API_KEY
    token = bot.api_key
    url = f"https://www.botobot.ru/api/v1/updateOrderStatus/{token}"

    if new_status == 'WCO':
        status = 10
    elif new_status == "CFD":
        status = 20
    elif new_status == "OND":
        status = 70
    elif new_status == "DLD":
        status = 90
    elif new_status == "CND":
        status = 30

    payload = {"id": order_id,
               "status": status}
    try:
        # Отправка POST-запроса
        response = requests.post(url, data=payload)
        response_data = response.json()
        reply_status = response_data.get('status')
        # Обработка ответа
        if response.status_code == 200 and reply_status == 'success':
            logger.info(f"TM order {order_id} "
                        f"status updated to {new_status} "
                        f"(status: {reply_status}).")
        else:
            error_message = response_data.get('message',
                                              'No error message provided')
            logger.error(f"Failed to update TM order {order_id} status to "
                         f"{new_status} "
                         f"(status: {reply_status}): {error_message}")

    except requests.RequestException as e:
        # Логирование ошибки запроса
        logger.error(f"Sending request failed for order {order_id} "
                     f"with status {new_status} (status: {str(e)}")

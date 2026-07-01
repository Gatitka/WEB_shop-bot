# например, в tm_bot/tasks.py или orders/tasks.py
from celery import shared_task
from django.db import transaction
from django.conf import settings
from shop.models import Order
from tm_bot.models import MessengerAccount, OrdersBot
from tm_bot.services import (send_status_update_message_to_client,
                             send_user_message_via_bot,
                             get_bot_id_by_city)
from tm_bot.text_assemble_and_edition import escape_markdown
import logging

logger = logging.getLogger(__name__)


@shared_task(
        queue="notifications",
        bind=True,
        max_retries=3,
        default_retry_delay=10)
def send_order_status_update_task(self, status: str, order_id: int):
    """
    Асинхронная отправка сообщения клиенту о смене статуса заказа.
    Получает только ID заказа и новый статус.
    """
    try:
        # можно оптимизировать select_related, если нужно
        order = Order.objects.select_related(
            "user__messenger_account"
        ).get(pk=order_id)
    except Order.DoesNotExist:
        logger.debug('Order is not found. Order id: %s', order_id)
        return f"Order {order_id} does not exist."
    try:
        send_status_update_message_to_client(status=status, order=order)
    except Exception as exc:
        # если хочешь ретраи на сетевых ошибках – можно так:
        raise self.retry(exc=exc)

    return "ok"


@shared_task(
        queue="notifications",
        bind=True,
        max_retries=3,
        default_retry_delay=10)
def send_link_confirmation_message(self, msngr_account_id, city):
    """
    Асинхронная отправка сообщения клиенту об успешной привязке телеграм-аккаунта.
    """
    try:
        # можно оптимизировать select_related, если нужно
        ma = MessengerAccount.objects.get(pk=msngr_account_id)
        bot = OrdersBot.objects.get(city=city)
        bot_token = settings.TELEGRAM_AUTH_BOTS.get(city)

    except MessengerAccount.DoesNotExist:
        return f"Messenger Account {msngr_account_id} does not exist."

    try:
        message = ("Отлично! Ваш Telegram-аккаунт теперь подключён. "
                   "Мы всегда на связи.")
        cleaned_message = escape_markdown(message)
        send_user_message_via_bot(messenger_account=ma,
                                  bot=bot,
                                  message=cleaned_message,
                                  bot_token=bot_token,
                                  )
    except Exception as exc:
        # если хочешь ретраи на сетевых ошибках – можно так:
        raise self.retry(exc=exc)

    return "ok"

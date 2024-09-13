import os
import django

# Настройка Django окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_shop_with_bots.settings')  # Замените 'your_project' на имя вашего проекта
django.setup()

from tm_bot.services import send_message_telegram


def send_bot_message():
    message = 'Ваш заказ передан курьеру\\.\nКоманда YUME SUSHI '
    send_message_telegram('6770543006', message)


if __name__ == '__main__':
    send_bot_message()
    print("Successfully sent message")

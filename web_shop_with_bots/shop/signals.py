import requests
from django.conf import settings
from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver

from shop.models import Order, OrderDish
from shop.services import find_uncomplited_cart_to_complete


@receiver(post_save, sender=Order)
def create_cart(sender, instance, created, **kwargs):
    """ Закрытие активной корзины после создания заказа."""
    if created:
        if instance.user is not None:
            find_uncomplited_cart_to_complete(instance.user)


@receiver(m2m_changed, sender=Order.dishes.through)
def send_message_new_order(sender, instance, action, **kwargs):
    """ Отправка сообщения телеграм-ботом в админский чат
        о новом заказе на сайте."""
    if kwargs['action'] == 'post_add':
        if instance.user and instance.user.messenger_account:
            msngr_acc = instance.user.messenger_account
            msngr_acc_rep = (
                f"({msngr_acc.msngr_type}) {msngr_acc.msngr_username}")
        else:
            msngr_acc_rep = ''

        message = (
            f"❗️Заказ на сайте 'Yume Sushi':\n"
            f"Номер #{instance.pk}.\n\n"

            "👉 Данные покупателя:\n"
            f"{instance.recipient_name}, {instance.recipient_phone}, "
            f"{msngr_acc_rep}\n\n"

            "📦 Доставка:\n"
            f"{instance.delivery.type}\n"
            # Адрес: Врачар,Кумановска 24, кв 5
            # Время: К 18:30
            #📝 Комментарий:
            #Заказ ко времени, на 18:30. Оплата наличными. Если интерфон не сработает сразу,просьба курьеру набрать меня

            "---\n"
            "🛒 Товары:\n"
            #1. Ролл Хоккайдо 1x1 000 din = 1 000 din, Вес 300 гр., Объем 8 шт.
            #2. Ролл Цезарь 1x1 000 din = 1 000 din, Вес 300 гр., Объем 8 шт.
            #3. Ролл Сакура 1x900 din = 900 din, Вес 320 гр., Объем 8 шт.


            #---
            f"Товары: {instance.discounted_amount} din\n"
            f"Доставка: {instance.delivery_cost} din\n")
            #"Итого: {instance.final_amount2 900 din")
        # Отправляем сообщение пользователю
        url = f'https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage'
        payload = {
            'chat_id': "194602954",
            'text': message
        }
        response = requests.post(url, data=payload)
        return response.json()

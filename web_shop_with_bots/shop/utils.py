from django.utils import timezone
from django.db.models import Max
from decimal import Decimal
from delivery_contacts.services import get_delivery_cost_zone
from promos.services import get_promocode_discount_amount


def get_reply_data_delivery(delivery, city, lat, lon,
                            cart=None,
                            orderdishes=None, promocode=None):

    amount = get_amount(cart, orderdishes)

    promocode, promocode_discount, discounted_amount = (
        get_promocode_promoc_disc_disc_amount(amount, cart, promocode)
    )

    delivery_discount = get_delivery_discount(delivery,
                                              discounted_amount)

    total_discount = Decimal(
        promocode_discount + delivery_discount).quantize(Decimal('0.01'))

    delivery_cost, delivery_zone = get_delivery_cost_zone(
                city, discounted_amount, delivery, lat, lon)

    reply_data = get_rep_dic_delivery(amount, promocode, total_discount,
                                      delivery, delivery_zone, delivery_cost,
                                      discounted_amount, delivery_discount)
    # total посчитается и оформится внутри

    return reply_data


def get_rep_dic_delivery(amount, promocode, total_discount,
                         delivery, delivery_zone, delivery_cost,
                         discounted_amount, delivery_discount):
    reply_data = {
        'amount': amount,
        'promocode': promocode,
        'total_discount': total_discount
    }

    reply_data = get_rep_dic(reply_data,
                             delivery, delivery_zone,
                             discounted_amount, delivery_discount,
                             delivery_cost)

    return reply_data


def get_rep_dic(reply_data,
                delivery=None, delivery_zone=None,
                discounted_amount=None, delivery_discount=None,
                delivery_cost=None,
                instance=None):

    if instance:
        delivery = instance.delivery
        delivery_zone = instance.delivery_zone

    if (delivery.type == 'delivery'
       and delivery_zone.name == 'уточнить'):

        if instance is None:
            total = (
                Decimal(discounted_amount) - Decimal(delivery_discount)
            )
        else:
            total = instance.discounted_amount

        reply_data['delivery_cost'] = "Requires clarification"
        reply_data['process_comment'] = (
            "Delivery address is outside our service area or "
            "an error occurred while processing the delivery data."
            "Please check with the administrator regarding "
            "the delivery possibility and it's cost."
        )

        reply_data['total'] = {
            "title": "Total amount, excl. delivery",
            "total_amount": total
            }

    else:
        if instance is None:
            total = (
                Decimal(discounted_amount) - Decimal(delivery_discount) +
                Decimal(delivery_cost)
            )

            reply_data['delivery_cost'] = delivery_cost

        else:
            total = instance.final_amount_with_shipping
            reply_data['delivery_cost'] = instance.delivery_cost

        reply_data['total'] = {
                "title": "Total amount, incl. delivery",
                "total_amount": total
                }

    return reply_data


def get_amount(cart=None, items=None):
    if cart:
        return cart.amount

    if items:
        amount = Decimal(0)
        for item in items:
            dish = item['dish']
            amount += Decimal(dish.final_price * item['quantity'])
        return amount


def get_promocode_promoc_disc_disc_amount(amount, cart=None, promocode=None):
    if cart:
        if cart.promocode is None:
            promocode_code = None
            promocode_discount = Decimal(0)
            discounted_amount = amount

        else:
            promocode_code = cart.promocode.promocode
            promocode_discount = cart.discount
            discounted_amount = cart.discounted_amount
        return promocode_code, promocode_discount, discounted_amount

    else:
        #  для незареганых пользователей
        if promocode is None:
            promocode_code = None
            promocode_discount = Decimal(0)
            discounted_amount = amount
        else:
            promocode_code = promocode.promocode
            promocode_discount = Decimal(
                amount * promocode.discount / Decimal(100)
            ).quantize(Decimal('0.01'))
            discounted_amount = Decimal(
                (amount - promocode_discount).quantize(Decimal('0.01'))
            )

        return promocode_code, promocode_discount, discounted_amount


def get_delivery_discount(delivery, discounted_amount):
    if delivery.discount:
        delivery_discount = (
            Decimal(discounted_amount)
            * Decimal(delivery.discount) / Decimal(100)
        ).quantize(Decimal('0.01'))
    else:
        delivery_discount = Decimal(0)
    return delivery_discount


def get_reply_data_takeaway(delivery,
                            cart=None,
                            orderdishes=None, promocode=None, ):

    amount = get_amount(cart, orderdishes)

    promocode, promocode_discount, discounted_amount = (
        get_promocode_promoc_disc_disc_amount(amount, cart, promocode)
    )
    delivery_discount = get_delivery_discount(delivery,
                                              discounted_amount)

    total_discount = Decimal(
        promocode_discount + delivery_discount).quantize(Decimal('0.01'))

    total = Decimal(
        discounted_amount - delivery_discount).quantize(Decimal('0.01'))

    reply_data = get_rep_dic_takeaway(amount, promocode, total_discount, total)

    return reply_data


def get_rep_dic_takeaway(amount, promocode, total_discount, total):
    reply_data = {
        'amount': amount,
        'promocode': promocode,
        'total_discount': total_discount,
        'total': {
            "title": "Total amount",
            "total_amount": total
            }
    }
    return reply_data


def get_repeat_order_form_data(order):
    repeat_order_form_data = {
        "recipient_name": order.recipient_name,
        "recipient_phone": str(order.recipient_phone),
        "city": order.city,
        "comment": order.comment,
        "persons_qty": order.persons_qty,
        "delivery": str(order.delivery.type),
    }

    if order.delivery.type == 'delivery':
        repeat_order_form_data['recipient_address'] = order.recipient_address
        repeat_order_form_data['delivery_zone'] = str(order.delivery_zone)

    elif order.delivery.type == 'takeaway':
        repeat_order_form_data['restaurant'] = order.restaurant

    return repeat_order_form_data


def get_next_item_id_today(model, field):
    today_start = timezone.localtime(
        timezone.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    # Начало текущего дня

    today_end = (
        today_start + timezone.timedelta(days=1)
        - timezone.timedelta(microseconds=1)  # Конец текущего дня
    )

    max_id = model.objects.filter(
        created__range=(today_start, today_end)
    ).aggregate(Max(field))[f'{field}__max']

    # Устанавливаем номер заказа на единицу больше MAX текущей даты
    if max_id is None:
        return 1
    else:
        return max_id + 1


def get_first_item_true(obj):
    # проверка на первый заказ
    model_class = obj.__class__
    if obj.user is not None:
        if not model_class.objects.filter(user=obj.user).exists():
            return True
    else:
        if not model_class.objects.filter(
            recipient_phone=obj.recipient_phone
        ).exists():
            return True
    return False


def get_cart_responce_dict(data, request):

    amount = get_amount(items=data.get('cartdishes'))

    promoc_disc_amount, message = get_promocode_discount_amount(
                            data.get('promocode'),
                            request, amount)
    cart_responce_dict = {
        # 'cartdishes': data.get('cartdishes'),
        'promocode': data.get('promocode').code,
        'amount': amount,
        'discount': promoc_disc_amount,
        'message': message,
        'discounted_amount': (amount - promoc_disc_amount)
    }
    return cart_responce_dict

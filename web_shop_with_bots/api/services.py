from delivery_contacts.services import get_delivery_cost_zone
from decimal import Decimal
from django.utils.translation import gettext_lazy as _

from shop.models import (get_amount, get_promocode_results,
                         get_delivery_discount, check_total_discount,
                         get_auth_first_order_discount,
                         cash_discount)

def get_reply_data_takeaway(delivery,
                            cart=None,
                            orderdishes=None, promocode=None,
                            request=None):

    amount = get_amount(cart, orderdishes)

    promocode_data, promocode_discount, free_delivery = (
        get_promocode_results(amount, promocode, request, cart)
    )

    delivery_discount = get_delivery_discount(delivery,
                                              amount)

    auth_fst_ord_disc, fo_status = get_auth_first_order_discount(
                                        amount,
                                        web_account=request.user)

    total_discount_sum = Decimal(
        promocode_discount + delivery_discount + auth_fst_ord_disc
        ).quantize(Decimal('0.01'))

    total_discount, disc_lim_message = check_total_discount(amount,
                                                            total_discount_sum)

    total = Decimal(
        amount - total_discount).quantize(Decimal('0.01'))

    reply_data = get_rep_dic_takeaway(amount, promocode_data,
                                      total_discount, total,
                                      disc_lim_message, fo_status)

    return reply_data


def get_rep_dic_takeaway(amount, promocode_data,
                         total_discount, total, disc_lim_message, fo_status):
    reply_data = {
        'amount': amount,
        'promocode': promocode_data,
        'total_discount': total_discount,
        'first_order': fo_status,
        'total': {
            "title": "Total amount",
            "total_amount": total
            },
        'detail': disc_lim_message
    }
    return reply_data


def get_reply_data_delivery(delivery, city, lat, lon,
                            cart=None,
                            orderdishes=None, promocode=None, payment_type=None,
                            language=None, request=None):

    amount = get_amount(cart, orderdishes)

    promocode_data, promocode_discount, free_delivery = (
        get_promocode_results(amount, promocode, request, cart)
    )

    delivery_discount = get_delivery_discount(delivery,
                                              amount)

    auth_fst_ord_disc, fo_status = get_auth_first_order_discount(
                                    amount,
                                    web_account=request.user)

    cash_disc = cash_discount(amount, payment_type, language)

    total_discount_sum = Decimal(
        promocode_discount + delivery_discount + auth_fst_ord_disc + cash_disc
        ).quantize(Decimal('0.01'))

    total_discount, disc_lim_message = check_total_discount(amount,
                                                            total_discount_sum)
    discounted_amount = Decimal(
        amount - total_discount).quantize(Decimal('0.01'))

    delivery_cost, delivery_zone = get_delivery_cost_zone(
                city, amount, delivery, lat, lon, free_delivery)
    # в расчет берется сумма заказа ДО скидок

    reply_data = get_rep_dic_delivery(amount, promocode_data, total_discount,
                                      discounted_amount, free_delivery,
                                      delivery, delivery_zone, delivery_cost,
                                      disc_lim_message, fo_status)
    # total посчитается и оформится внутри

    return reply_data


def get_rep_dic_delivery(amount, promocode_data, total_discount,
                         pre_total, free_delivery,
                         delivery, delivery_zone, delivery_cost,
                         disc_lim_message, fo_status):
    reply_data = {
        'amount': amount,
        'promocode': promocode_data,
        'total_discount': total_discount,
        'first_order': fo_status
    }

    reply_data = get_rep_dic(reply_data, free_delivery,
                             delivery, delivery_zone,
                             pre_total, delivery_cost,
                             disc_lim_message)

    return reply_data


def get_rep_dic(reply_data, free_delivery=False,
                delivery=None, delivery_zone=None,
                pre_total=None, delivery_cost=None,
                disc_lim_message=None,
                instance=None):

    if instance:
        delivery = instance.delivery
        delivery_zone = instance.delivery_zone

    if (delivery.type == 'delivery'
       and delivery_zone.name == 'уточнить'):

        if instance is None:
            total = pre_total
        else:
            total = instance.discounted_amount

        reply_data['delivery_cost'] = "Requires clarification"
        reply_data['total'] = {
                "title": "Total amount, excl. delivery",
                "total_amount": total
                }

        if not free_delivery:

            reply_data['detail'] = (
                "Delivery address is outside our service area or "
                "an error occurred while processing the delivery data. "
                "Please check with the administrator regarding "
                "the delivery possibility and it's cost."
            )

        else:
            reply_data['detail'] = (
                "Delivery address is outside our service area or "
                "an error occurred while processing the delivery data. "
                "Please check with the administrator regarding "
                "the delivery possibility and free delivery promocode."
            )

    else:
        if instance is None:
            total = pre_total + delivery_cost

            reply_data['delivery_cost'] = delivery_cost

        else:
            total = instance.final_amount_with_shipping
            reply_data['delivery_cost'] = instance.delivery_cost

        reply_data['total'] = {
                "title": "Total amount, incl. delivery",
                "total_amount": total
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


def get_promoc_resp_dict(data, request):

    promocode = data.get('promocode')

    if promocode:

        promoc_resp_dict = {"promocode": promocode.code,
                            "code": "valid"}

        if promocode.ttl_am_discount_percent:

            promoc_resp_dict['detail'] = (
                _("%(perc)s%% discount accepted for the order.")
                % {"perc": promocode.ttl_am_discount_percent}
            )

        elif promocode.ttl_am_discount_amount:

            promoc_resp_dict['detail'] = (
                _("%(amnt)s RSD discount accepted for the order.")
                % {"amnt": promocode.ttl_am_discount_amount}
            )

        elif promocode.free_delivery:

            promoc_resp_dict['detail'] = (
                _("Free delivery accepted for the order.")
            )

        elif promocode.gift:

            promoc_resp_dict['detail'] = (
                _("Within the promotion, you will receive a gift.")
            )

    else:
        promoc_resp_dict = {"promocode": None,
                            "detail": _("Promocode is deleted."),
                            "code": "invalid"}

    # amount = get_amount(items=data.get('cartdishes'))

    # promocode = data.get('promocode')

    # promoc_disc_amount, message, free_delivery = (
    #     get_promocode_discount_amount(promocode, amount,
    #                                   request))
    # if promocode:
    #     promocode_dict = {"promocode": promocode.code,
    #                       "status": "valid"}
    # else:
    #     promocode_dict = {"promocode": None,
    #                       "status": "no_status"}

    # cart_responce_dict = {
    #     # 'cartdishes': data.get('cartdishes'),
    #     'promocode': promocode_dict,
    #     'amount': amount,
    #     'discount': promoc_disc_amount,
    #     'message': message,
    #     'discounted_amount': (amount - promoc_disc_amount)
    # }

    return promoc_resp_dict

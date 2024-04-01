from decimal import Decimal


def get_promocode_discount_amount(promocode, amount=None,
                                  request=None):

    promoc_disc_amount = Decimal(0)
    message = ''
    free_delivery = False

    if not promocode:
        return promoc_disc_amount, message, free_delivery

    # проверка на первый заказ осуществляется в сериализаторе и форме (админ)
    # if promocode.first_order:
    #     message = ("This promo code is applicable only for the first order. "
    #                "Will be applied after order form filling in.")
    #     return promoc_disc_amount, message, free_delivery

    if promocode.free_delivery:
    #     message = ("The promo code will be applied after "
    #                 "filling out the order form.")
        free_delivery = True

    elif promocode.gift:
        message = "A gift as part of the promotion awaits you."

    else:
        promoc_disc_amount = (
            calculate_promoc_discount_amount(promocode, amount))

    return promoc_disc_amount, message, free_delivery


def calculate_promoc_discount_amount(promocode, amount):
    if promocode.ttl_am_discount_percent:
        promoc_disc_amount = (
            Decimal(amount) * Decimal(promocode.ttl_am_discount_percent)
            / Decimal(100)).quantize(Decimal('0.01'))

    elif promocode.ttl_am_discount_amount:
        promoc_disc_amount = promocode.ttl_am_discount_amount

    return promoc_disc_amount

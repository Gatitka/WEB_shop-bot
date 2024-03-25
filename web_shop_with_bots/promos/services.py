from decimal import Decimal


def get_promocode_discount_amount(promocode,
                                  request=None, amount=None, first_order=False):

    promoc_disc_amount = Decimal(0)
    message = ''

    if not promocode:
        return promoc_disc_amount, message

    if promocode.first_order:
        if not first_order(request):
            message = "Promocode isn't allowed as you have orders history."

        elif promocode.free_delivery:
            message = ("The promo code will be applied after "
                       "filling out the order form.")

        elif promocode.gift:
            message = "A gift as part of the promotion awaits you."

        else:
            promoc_disc_amount = (
                calculate_promoc_discount_amount(promocode, amount))

    else:
        if promocode.free_delivery:
            message = ("The promo code will be applied after "
                       "filling out the order form.")

        elif promocode.gift:
            message = "A gift as part of the promotion awaits you."

        else:
            promoc_disc_amount = (
                calculate_promoc_discount_amount(promocode, amount))

    return promoc_disc_amount, message


def calculate_promoc_discount_amount(promocode, amount):
    if promocode.ttl_am_discount_percent:
        promoc_disc_amount = (
            Decimal(amount) * Decimal(promocode.ttl_am_discount_percent)
            / Decimal(100)).quantize(Decimal('0.01'))

    elif promocode.ttl_am_discount_amount:
        promoc_disc_amount = (
            Decimal(amount) - Decimal(promocode.ttl_am_discount_amount)
            ).quantize(Decimal('0.01'))

    return promoc_disc_amount

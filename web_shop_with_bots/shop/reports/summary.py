from decimal import Decimal

from django.conf import settings


def get_report_data(orders_list):
    # Разбираем заказы по типам для дальнейшего анализа
    delivery_orders = []
    takeaway_orders = []
    partners_orders = []
    restaurant_orders = []
    for order in orders_list:
        if order.delivery.type == 'delivery':
            delivery_orders.append(order)

        elif order.delivery.type == 'restaurant':
            takeaway_orders.append(order)
            restaurant_orders.append(order)
        elif order.delivery.type == 'takeaway':
            takeaway_orders.append(order)
            if order.source in settings.PARTNERS_LIST:
                partners_orders.append(order)

    total_amount = sum(order.final_amount_with_shipping for order in orders_list)
    total_qty = orders_list.count()
    total_discounts_amount = sum(order.discount_amount for order in orders_list)

    total_nocash = (
        sum(
            order.final_amount_with_shipping
            for order in orders_list
            if order.source != 'P2-2'
            and order.payment_type == 'cash'
            and order.invoice is False
        )
    )
    total_gotovina = sum(
        order.final_amount_with_shipping
        for order in orders_list
        if order.payment_type == 'cash' and order.invoice is True
    )
    takeaway_gotovina_for_cash_total = sum(
        order.final_amount_with_shipping
        for order in takeaway_orders
        if order.payment_type == 'cash' and order.invoice is True
    )
    takeaway_nocash = (
        sum(
            order.final_amount_with_shipping
            for order in takeaway_orders
            if order.source != 'P2-2'
            and order.payment_type == 'cash'
            and order.invoice is False
        )
    )
    takeaway_gotovina = total_gotovina
    takeaway_card = sum(
        order.final_amount_with_shipping
        for order in takeaway_orders
        if order.payment_type in ['card', 'card_on_delivery']
    )

    restaurant_am = sum(
        order.final_amount_with_shipping
        for order in restaurant_orders
    )

    source_dict = dict(settings.SOURCE_TYPES)
    partners = {}
    for order in partners_orders:
        partner_name = source_dict[order.source]
        partners[partner_name] = (
            partners.get(partner_name, Decimal('0'))
            + order.final_amount_with_shipping
        )
    if 'Не та дверь' in partners:
        partners['Ne_ta_dver'] = partners.pop('Не та дверь')

    total_smoke = partners.get('Smoke', Decimal('0'))
    total_ne_ta = partners.get('Ne_ta_dver', Decimal('0'))
    total_curiers_show = sum(
        order.final_amount_with_shipping
        for order in delivery_orders
        if order.payment_type == 'cash'
    )
    total_terminal = total_amount - total_nocash - total_smoke - total_ne_ta

    couriers = get_couriers_data(delivery_orders)
    total_cash = get_cash_report_total(
        couriers,
        takeaway_nocash,
        takeaway_gotovina_for_cash_total,
    )
    drugo_bezgotovinsko = get_bezgotovinsko_report_total(couriers, partners)

    return {
        'total_amount': f"{total_amount:.2f} ({total_qty} зак.)",
        'takeaway_nocash': float(takeaway_nocash),
        'takeaway_gotovina': float(takeaway_gotovina),
        'takeaway_card': takeaway_card,
        'restaurant_am': restaurant_am,
        'total_curiers': total_curiers_show,
        'total_terminal': total_terminal,
        'partners': partners,
        'couriers': couriers,
        'total_cash': total_cash,
        'drugo_bezgotovinsko': drugo_bezgotovinsko,
        'total_discounts_amount': total_discounts_amount,
    }


def get_couriers_data(delivery_orders):
    """
    couriers = {
        'courier_name': [
            Decimal('0') - сумма доставок для оплаты курьеру,
            Bool - есть ли "уточнить",
            Decimal('0') - сумма заказов безнал,
            Decimal('0') - сумма заказов нал,
            Decimal('0') - сумма заказов безнал + нал,
            Decimal('0') - сумма заказов карта,
            Decimal('0') - сумма минимальной оплаты за выход,
        ],
        'total_cash': Dec,
        'total_bezgotovinsko': Dec,
    }
    """
    if not delivery_orders:
        return {'Нет курьеров': [0, False, 0, 0, 0, 0, 0]}

    couriers = {}
    courier_days = {}

    for order in delivery_orders:
        courier_name = order.courier if order.courier else 'Unknown'
        unclarified = False
        courier_days = couriers_working_days(order, courier_name, courier_days)

        if order.delivery_zone.delivery_cost != float(0):
            delivery_cost = order.delivery_zone.delivery_cost
        elif order.delivery_zone.name == 'уточнить':
            delivery_cost = order.delivery_cost
            unclarified = True
        elif order.delivery_zone.name == 'по запросу':
            delivery_cost = order.delivery_cost
        else:
            delivery_cost = Decimal('0')

        if courier_name in couriers:
            couriers[courier_name][0] -= delivery_cost
        else:
            couriers[courier_name] = [
                Decimal('0'),
                False,
                Decimal('0'),
                Decimal('0'),
                Decimal('0'),
                Decimal('0'),
                Decimal('0'),
            ]
            if order.courier:
                couriers[courier_name][6] = order.courier.min_payout
            couriers[courier_name][0] = Decimal('0') - delivery_cost

        couriers[courier_name][1] = unclarified

        if order.payment_type == 'cash' and order.invoice is False:
            couriers[courier_name][2] += order.final_amount_with_shipping
            couriers[courier_name][4] += order.final_amount_with_shipping
        elif order.payment_type == 'cash' and order.invoice is True:
            couriers[courier_name][3] += order.final_amount_with_shipping
            couriers[courier_name][4] += order.final_amount_with_shipping
        elif order.payment_type in ['card', 'card_on_delivery']:
            couriers[courier_name][5] += order.final_amount_with_shipping

    return get_correct_min_payout_and_totals(couriers, courier_days)


def get_cash_report_total(curiers, takeaway_nocash, takeaway_gotovina):
    total_cash = Decimal('0')
    if 'total_cash' in curiers:
        total_cash += curiers['total_cash']
    total_cash += takeaway_nocash
    total_cash += takeaway_gotovina
    return total_cash


def get_bezgotovinsko_report_total(curiers, partners):
    drugo_bezgotovinsko = Decimal('0')
    if 'total_bezgotovinsko' in curiers:
        drugo_bezgotovinsko += curiers['total_bezgotovinsko']
    for partner, total_value in partners.items():
        if partner in ['Glovo', 'Wolt']:
            drugo_bezgotovinsko += total_value
    return drugo_bezgotovinsko


def couriers_working_days(order, courier_name, courier_days):
    working_date = None
    if getattr(order, 'execution_date', None):
        working_date = order.execution_date
    elif getattr(order, 'delivery_time', None):
        working_date = order.delivery_time.date()
    else:
        working_date = order.created.astimezone(None).date()

    if courier_name not in courier_days:
        courier_days[courier_name] = set()
    courier_days[courier_name].add(working_date)
    return courier_days


def get_correct_min_payout_and_totals(couriers, courier_days):
    total_cash = Decimal('0')
    total_bezgotovinsko = Decimal('0')

    for courier_name, results in couriers.items():
        day_count = len(courier_days.get(courier_name, set()))
        daily_min = results[6]
        results[6] = (daily_min * day_count) if daily_min else Decimal('0')
        results[0] -= results[6]

        total_cash += results[0]
        total_cash += results[4]
        total_bezgotovinsko += results[5]

    couriers.update({
        'total_cash': total_cash,
        'total_bezgotovinsko': total_bezgotovinsko,
    })
    return couriers

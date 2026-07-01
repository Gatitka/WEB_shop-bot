from django.conf import settings
from django.utils import timezone


def get_takeaway_source_label(order):
    if order.source in ['1', '3', '4']:
        return 'самовывоз'
    if order.source == 'P1-1':
        return 'GLOVO'
    if order.source == 'P1-2':
        return 'WOLT'
    if order.source == 'P2-1':
        return 'SMOKE'
    if order.source == 'P2-2':
        return 'NE TA'
    if order.source == 'P3-1':
        return 'SEAL TEA'
    return 'самовывоз'


def get_short_order_address(order):
    if order.delivery:
        if order.delivery.type == 'delivery':
            return order.recipient_address
        if order.delivery.type == 'restaurant':
            return "ресторан"
    return get_takeaway_source_label(order)


def get_local_dt(value):
    if value is None:
        return None
    if timezone.is_aware(value):
        return timezone.localtime(value)
    return value


def get_dish_name_ru(dish):
    if dish is None:
        return '[DELETED DISH]'

    translations = getattr(dish, 'translations', None)
    if translations is None:
        return '[NO RU TRANSLATION]'

    for tr in translations.all():
        if getattr(tr, 'language_code', None) == 'ru':
            return (
                getattr(tr, 'short_name', None)
                or getattr(tr, 'name', None)
                or '[NO RU TRANSLATION]'
            )

    return '[NO RU TRANSLATION]'


def build_short_orders_headers():
    return [
        'Заказ',
        'ID Заказа',
        'Дата',
        'Время',
        'Адрес',
        'Сумма',
        'N',
        'Чек',
        'Примечание',
        'Стоимость доставки',
        'Статус',
        'Курьер',
        'Рекламная кампания'
    ]


def build_short_order_row(order):
    invoice = 1 if order.invoice else ''
    note = order.source_id if order.source in (['3'] + settings.PARTNERS_LIST) else ''
    courier = str(order.courier) if order.courier is not None else ''
    created_local = get_local_dt(order.created)

    return [
        order.order_number,
        order.id,
        created_local.strftime('%Y-%m-%d') if created_local else '',
        created_local.strftime('%H:%M:%S') if created_local else '',
        get_short_order_address(order),
        order.final_amount_with_shipping,
        order.payment_type,
        invoice,
        note,
        order.delivery_cost,
        order.status,
        courier,
        order.campaign
    ]


def build_full_orders_headers():
    return [
        'Order_Num', 'ID', 'Source',
        'Day', 'Month', 'Year', 'Time',
        'City', 'Restaurant ID',
        'Status', 'Is_first_order', 'Created_by',
        'User', 'Name', 'Phone',
        'MSNGR_ID', 'MSNGR_USERNAME',
        'Delivery', 'Delivery_Time',
        'Address', 'Delivery_Zone', 'Courier',
        'Payment', 'Invoice',
        'Discount', 'Delivery_Cost',
        'Discount_amount', 'Manual_discount',
        'Amount', 'Discounted_amount', 'Final_amount_with_shipping',
        'Campaign'
    ]


def build_full_order_row(order):
    created_local = get_local_dt(order.created)
    delivery_time_local = get_local_dt(order.delivery_time)

    return [
        order.order_number,
        order.id,
        str(order.source),
        # created_local.strftime('%Y-%m-%d') if created_local else '',
        created_local.day if created_local else '',
        created_local.month if created_local else '',
        created_local.year if created_local else '',
        created_local.strftime('%H:%M:%S') if created_local else '',
        order.city,
        order.restaurant_id,
        order.status,
        'yes' if order.is_first_order else '',
        order.created_by,
        str(order.user.id) if order.user is not None else '',
        order.recipient_name,
        str(order.recipient_phone),
        order.msngr_account.msngr_id if order.msngr_account is not None else '',
        order.msngr_account.msngr_username if order.msngr_account is not None else '',
        order.delivery.type if order.delivery is not None else '',
        delivery_time_local.strftime('%Y-%m-%d %H:%M:%S') if delivery_time_local else None,
        order.recipient_address,
        str(order.delivery_zone),
        str(order.courier),
        order.payment_type,
        'yes' if order.invoice else '',
        str(order.discount),
        order.delivery_cost,
        order.discount_amount,
        order.manual_discount,
        order.amount,
        order.discounted_amount,
        order.final_amount_with_shipping,
        order.campaign,
    ]


def build_order_items_headers():
    return [
        'Order_ID', 'Order_Num',
        # 'Date',
        'Day', 'Month', 'Year', 'Time',
        'Source', 'Status',
        'Delivery', 'Payment',
        'Dish_article', # 'Dish_name_ru',
        'Qty', 'Unit_price', 'Unit_amount',
        'Order_amount', 'Order_discounted_amount', 'Order_final_amount',
        # 'Client_name', 'Client_phone', 'Address', 'Courier',
    ]


def build_order_item_row(item):
    order = item.order
    dish = item.dish
    created_local = get_local_dt(order.created)

    return [
        order.id,
        order.order_number,
        # created_local.strftime('%Y-%m-%d') if created_local else '',
        created_local.day if created_local else '',
        created_local.month if created_local else '',
        created_local.year if created_local else '',
        created_local.strftime('%H:%M:%S') if created_local else '',
        order.source,
        order.status,
        order.delivery.type if order.delivery is not None else '',
        order.payment_type or '',
        # getattr(dish, 'id', ''),
        getattr(dish, 'article', ''),
        # get_dish_name_ru(dish),
        item.quantity,
        item.unit_price,
        item.unit_amount,
        order.amount,
        order.discounted_amount,
        order.final_amount_with_shipping,
        # order.recipient_name or '',
        # str(order.recipient_phone or ''),
        # order.recipient_address or '',
        # str(order.courier or ''),
    ]

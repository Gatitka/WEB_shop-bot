from django.contrib.admin.views.decorators import staff_member_required
from shop.models import Order, OrderDish
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.db.models.functions import TruncDay
import datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from django.conf import settings
from django.db.models import Prefetch


@staff_member_required
def sales_data(request):
    """Отчет по продажам за последний месяц на начальной странице.
    Разделяет типы заказов с сайта/ботоа.
    Для админов ресторанов показывается статистика их ресторана. Для суперюзера полная статистика."""
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    date_range = [(last_30_days + timedelta(days=i)) for i in range(31)]

    def fill_missing_dates(queryset, date_range):
        data_dict = {entry['day'].date(): entry['total'] for entry in queryset}
        filled_data = [{'day': day, 'total': data_dict.get(day, 0)} for day in date_range]
        return filled_data

    def fill_missing_order_dates(queryset, date_range):
        data_dict = {entry['day'].date(): entry['total_orders'] for entry in queryset}
        filled_data = [{'day': day, 'total_orders': data_dict.get(day, 0)} for day in date_range]
        return filled_data

    restaurant_title = None
    if not request.user.is_superuser:
        base_filter_ = Q(created__gte=timezone.make_aware(
                            datetime.datetime.combine(
                                last_30_days,
                                datetime.datetime.min.time())))
        restaurant = request.user.restaurant
        restaurant_title = str(restaurant)
        rest_filter = Q(restaurant=restaurant.id)
        base_filter = base_filter_ & rest_filter
    else:
        base_filter = Q(created__gte=timezone.make_aware(
                                datetime.datetime.combine(
                                    last_30_days,
                                    datetime.datetime.min.time())))
    web_filter = Q(source='4')
    bot_filter = Q(source='3')

    base_filter_q = base_filter
    base_web_filter_q = base_filter & web_filter
    base_bot_filter_q = base_filter & bot_filter

    user = request.user

    # Запросы для подсчета общих продаж по дням
    total_sales_qs = Order.objects.filter(
            base_filter_q
        ).annotate(day=TruncDay('created')).values('day').annotate(
            total=Sum('final_amount_with_shipping')
        ).order_by('day')
    total_sales = fill_missing_dates(total_sales_qs, date_range)

    # Запросы для подсчета продаж с сайта (source='4') по дням
    site_sales_qs = Order.objects.filter(
            base_web_filter_q
        ).annotate(day=TruncDay('created')).values('day').annotate(
            total=Sum('final_amount_with_shipping')
        ).order_by('day')
    site_sales = fill_missing_dates(site_sales_qs, date_range)

    # Запросы для подсчета продаж с бота (source='3') по дням
    bot_sales_qs = Order.objects.filter(
            base_bot_filter_q
        ).annotate(day=TruncDay('created')).values('day').annotate(
            total=Sum('final_amount_with_shipping')
        ).order_by('day')
    bot_sales = fill_missing_dates(bot_sales_qs, date_range)

    # Запросы для подсчета общего количества заказов по дням
    total_orders_qs = Order.objects.filter(
            base_filter_q
        ).annotate(day=TruncDay('created')).values('day').annotate(
            total_orders=Count('id')
        ).order_by('day')
    total_orders = fill_missing_order_dates(total_orders_qs, date_range)

    # Запросы для подсчета количества заказов с сайта (source='4') по дням
    site_orders_qs = Order.objects.filter(
            base_web_filter_q
        ).annotate(day=TruncDay('created')).values('day').annotate(
            total_orders=Count('id')
        ).order_by('day')
    site_orders = fill_missing_order_dates(site_orders_qs, date_range)

    # Запросы для подсчета количества заказов с бота (source='3') по дням
    bot_orders_qs = Order.objects.filter(
            base_bot_filter_q
        ).annotate(day=TruncDay('created')).values('day').annotate(
            total_orders=Count('id')
        ).order_by('day')
    bot_orders = fill_missing_order_dates(bot_orders_qs, date_range)

    data = {
        'total_sales': total_sales,
        'site_sales': site_sales,
        'bot_sales': bot_sales,
        'total_orders': total_orders,
        'site_orders': site_orders,
        'bot_orders': bot_orders,
    }

    for key, value in data.items():
        for item in value:
            item['day'] = datetime.datetime.combine(
                item['day'],
                datetime.datetime.min.time())
    data['restaurant'] = restaurant_title
    return JsonResponse(data)


# ------------------------ ПЕЧАТЬ ЧЕКОВ ----------------------------

def get_receipt_data(order_id):
    """Get formatted receipt data for printing"""
    try:
        order = Order.objects.select_related(
            'delivery',
        ).prefetch_related(
            Prefetch(
                    'orderdishes',
                    queryset=OrderDish.objects.all().select_related(
                        'dish'
                    ).prefetch_related(
                        'dish__translations'
                    )
                )
        ).get(id=order_id)

        # Format receipt data
        receipt_data = {
            'order_number': f"#{order.order_number}",
            'date': order.created.strftime('%d.%m.%Y %H:%M'),
            'customer': {
                # 'name': order.recipient_name,
                # 'phone': order.recipient_phone,
                'address': order.recipient_address if order.delivery.type == 'delivery' else 'Самовывоз'
            },
            'items': [{
                'name': item.dish.safe_translation_getter('short_name', language_code='ru', any_language=True),
                'quantity': item.quantity,
            } for item in order.orderdishes.all()],
            'persons_qty': int(order.persons_qty),
            'source_data': get_source_display(order)
        }

        return Response(receipt_data)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=404)


def get_source_display(order):
    """Get display name for order source"""
    source_dict = dict(settings.SOURCE_TYPES)
    if order.source in settings.PARTNERS_LIST:
        return f"{source_dict.get(order.source)} {order.source_id}"
    return ""


class PrinterCommands:
    """ESC/POS printer commands"""
    INIT = '\x1B\x40'  # Initialize printer
    LF = '\x0A'        # Line feed
    CR = '\x0D'        # Carriage return
    CRLF = '\x0D\x0A'  # Комбинируем CR и LF в одну команду

    # Alignment
    ALIGN_LEFT = '\x1B\x61\x00'
    ALIGN_CENTER = '\x1B\x61\x01'
    ALIGN_RIGHT = '\x1B\x61\x02'

    # Text format
    BOLD_ON = '\x1B\x45\x01'
    BOLD_OFF = '\x1B\x45\x00'
    DOUBLE_WIDTH_ON = '\x1B\x0E'
    DOUBLE_WIDTH_OFF = '\x1B\x14'
    DOUBLE_HEIGHT_ON = '\x1B\x21\x10'
    DOUBLE_HEIGHT_OFF = '\x1B\x21\x00'

    # Paper cut
    PARTIAL_CUT = '\x1B\x6D'

    @classmethod
    def set_size(cls, width=1, height=1):
        """Set text size (1-8 for both width and height)"""
        if not (1 <= width <= 8 and 1 <= height <= 8):
            raise ValueError("Width and height must be between 1 and 8")
        size = (width - 1) | ((height - 1) << 4)
        return f'\x1D\x21{chr(size)}'


def format_receipt(receipt_data):
    """Format receipt text with printer control codes for 72mm paper"""
    cmd = PrinterCommands
    receipt = []
    LINE_WIDTH = 48  # Maximum characters per line for 72mm paper

    # Initialize printer and reset formatting
    receipt.append(cmd.INIT)
    receipt.append(cmd.set_size(1, 1))
    receipt.append(cmd.ALIGN_LEFT)
    receipt.append(cmd.BOLD_OFF)

    # Order number - centered, large and bold
    receipt.append(cmd.ALIGN_CENTER)
    # Name in bold
    receipt.append(cmd.BOLD_ON) # Добавляем жирный шрифт для номера
    receipt.append(cmd.set_size(3, 3))  # Самый большой размер для номера
    receipt.append(receipt_data['order_number'])
    receipt.append(cmd.set_size(1, 1))  # Сброс размера
    receipt.append(cmd.BOLD_OFF) # Отключаем жирный после номера
    receipt.append(cmd.LF)  # Достаточно только LF
    receipt.append(cmd.LF)  # Второй LF для дополнительного отступа

    # Menu items - left aligned
    # А вот для выровненного по левому/правому краю текста нужен CR+LF
    receipt.append(cmd.ALIGN_LEFT)
    receipt.append(cmd.set_size(1, 2))  # Средний размер для блюд
    for item in receipt_data['items']:
        name = item['name'].upper()
        qty = str(item['quantity'])

        # Calculate dots
        available_space = LINE_WIDTH - len(name) - len(qty)
        dots = '.' * available_space if available_space > 0 else ' '

        receipt.append(name)
        receipt.append(dots)
        receipt.append(qty)
        receipt.append(cmd.CRLF)

    receipt.append(cmd.set_size(1, 1))  # Сброс размера
    receipt.append(cmd.LF)

    # Service info - left aligned
    receipt.append(cmd.ALIGN_LEFT)
    receipt.append(f"приборы - {receipt_data['persons_qty']} шт.")
    receipt.append(cmd.CRLF)

    # Address
    receipt.append(receipt_data['customer']['address'])
    receipt.append(cmd.CRLF)

    # Partner info if exists - right aligned
    if receipt_data['source_data']:
        receipt.append(cmd.ALIGN_RIGHT)
        receipt.append(cmd.set_size(2, 2))  # Увеличенный размер для источника
        receipt.append(cmd.BOLD_ON)     # Добавляем жирный шрифт для номера
        source_text = receipt_data['source_data']
        if len(source_text) > LINE_WIDTH:
            source_text = source_text[-LINE_WIDTH:]
        receipt.append(source_text)
        receipt.append(cmd.set_size(1, 1))  # Сброс размера
        receipt.append(cmd.BOLD_OFF)    # Отключаем жирный после номера
        receipt.append(cmd.CRLF)

    # Feed and cut
    receipt.append(cmd.LF * 5)     # Extra feed for clean cut
    receipt.append(cmd.PARTIAL_CUT)

    return ''.join(receipt)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@staff_member_required
def get_formatted_receipt(request, order_id):
    """Get fully formatted receipt ready for printing"""
    try:
        # Получаем данные чека
        receipt_response = get_receipt_data(order_id)
        if isinstance(receipt_response, Response) and receipt_response.status_code != 200:
            return receipt_response

        receipt_data = receipt_response.data
        formatted_receipt = format_receipt(receipt_data)

        return Response({
            'receipt_text': formatted_receipt,
            'printer_settings': {
                'codepage': 'CP866',    # Кодировка для кириллицы
                'chars_per_line': 48,   # Ширина чека в символах
                'paper_width': 72,      # Ширина бумаги в мм
                'cut_paper': True       # Обрезка чека
            }
        })

    except Exception as e:
        return Response({'error': str(e)}, status=500)

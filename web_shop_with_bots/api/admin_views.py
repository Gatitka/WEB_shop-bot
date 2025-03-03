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


STANDARD_HEIGHT_ITEMS = 6  # Standard height is based on 6 items


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
    INIT = b'\x1B\x40'  # Initialize printer
    LF = b'\x0A'        # Line feed
    CR = b'\x0D'        # Carriage return
    CRLF = b'\x0D\x0A'  # Комбинируем CR и LF в одну команду

    # Кодовые страницы для кириллицы
    CODEPAGE_CP866 = b'\x1B\x74\x11'     # ESC t 17 - DOS кириллица

    # Alignment
    ALIGN_LEFT = b'\x1B\x61\x00'
    ALIGN_CENTER = b'\x1B\x61\x01'
    ALIGN_RIGHT = b'\x1B\x61\x02'

    # Text format
    BOLD_ON = b'\x1B\x45\x01'
    BOLD_OFF = b'\x1B\x45\x00'
    DOUBLE_WIDTH_ON = b'\x1B\x0E'
    DOUBLE_WIDTH_OFF = b'\x1B\x14'
    DOUBLE_HEIGHT_ON = b'\x1B\x21\x10'
    DOUBLE_HEIGHT_OFF = b'\x1B\x21\x00'

    # Более точные команды для размера шрифта
    DOUBLE_HEIGHT = b'\x1B\x21\x10'  # Double height text
    DOUBLE_WIDTH = b'\x1B\x21\x20'   # Double width text
    DOUBLE_BOTH = b'\x1B\x21\x30'    # Double height and width
    NORMAL_SIZE = b'\x1B\x21\x00'    # Normal size text

    # Paper cut
    PARTIAL_CUT = b'\x1D\x56\x01'   # GS V 1 - Стандартная команда обрезки

    @classmethod
    def set_size(cls, width=1, height=1):
        """Set text size (1-8 for both width and height)"""
        if not (1 <= width <= 8 and 1 <= height <= 8):
            raise ValueError("Width and height must be between 1 and 8")
        size = (width - 1) | ((height - 1) << 4)
        return b'\x1D\x21' + bytes([size])


def format_receipt(receipt_data, codepage='CP866'):
    """Format receipt text with printer control codes for 72mm paper"""
    cmd = PrinterCommands
    receipt = bytearray()  # Используем bytearray вместо списка строк
    LINE_WIDTH = 48  # Maximum characters per line for 72mm paper

    # Initialize printer and reset formatting
    receipt.extend(cmd.INIT)
    receipt.extend(cmd.CODEPAGE_CP866)  # Используем CP866 как самый надежный вариант
    receipt.extend(cmd.NORMAL_SIZE)
    receipt.extend(cmd.ALIGN_LEFT)
    receipt.extend(cmd.BOLD_OFF)

     # Calculate how many items we have and add extra space at the top if needed
    items_count = len(receipt_data['items'])

    # If we have fewer than the standard number of items, add extra line feeds at the top
    if items_count < STANDARD_HEIGHT_ITEMS:
        extra_lines_needed = (STANDARD_HEIGHT_ITEMS - items_count) * 2  # Each item takes approximately 2 lines
        for _ in range(extra_lines_needed):
            receipt.extend(cmd.LF)

    # Order number - centered, large and bold
    receipt.extend(cmd.ALIGN_LEFT)
    receipt.extend(cmd.BOLD_ON)
    receipt.extend(cmd.DOUBLE_BOTH)  # Увеличенные номера заказа
    receipt.extend(str(receipt_data['order_number']).encode('cp866'))
    receipt.extend(cmd.NORMAL_SIZE)
    receipt.extend(cmd.BOLD_OFF)
    receipt.extend(cmd.LF)
    receipt.extend(cmd.LF)

    # Menu items - left aligned
    receipt.extend(cmd.ALIGN_LEFT)
    receipt.extend(cmd.DOUBLE_HEIGHT)  # Средний размер для блюд
    for item in receipt_data['items']:
        name = item['name'].upper()
        qty = str(item['quantity'])

        # Calculate dots
        available_space = LINE_WIDTH - len(name) - len(qty)
        dots = '.' * available_space if available_space > 0 else ' '

        line = name + dots + qty
        receipt.extend(line.encode('cp866'))
        receipt.extend(cmd.CRLF)

    receipt.extend(cmd.NORMAL_SIZE)
    receipt.extend(cmd.LF)

    # Service info - left aligned
    receipt.extend(cmd.ALIGN_LEFT)
    service_text = f"приборы - {receipt_data['persons_qty']} шт."
    receipt.extend(service_text.encode('cp866'))
    receipt.extend(cmd.CRLF)

    # Address
    address_text = receipt_data['customer']['address']
    receipt.extend(address_text.encode('cp866'))
    receipt.extend(cmd.CRLF)

    # Partner info if exists - right aligned
    if receipt_data['source_data']:
        receipt.extend(cmd.ALIGN_RIGHT)
        receipt.extend(cmd.DOUBLE_WIDTH)  # Увеличенный размер для источника
        receipt.extend(cmd.BOLD_ON)
        source_text = receipt_data['source_data']
        if len(source_text) > LINE_WIDTH:
            source_text = source_text[-LINE_WIDTH:]
        receipt.extend(source_text.encode('cp866'))
        receipt.extend(cmd.NORMAL_SIZE)
        receipt.extend(cmd.BOLD_OFF)
        receipt.extend(cmd.CRLF)

    # Feed and cut
    for _ in range(5):
        receipt.extend(cmd.LF)  # Extra feed for clean cut
    receipt.extend(cmd.PARTIAL_CUT)

    return receipt


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@staff_member_required
def get_formatted_receipt(request, order_id):
    """Get fully formatted receipt ready for printing"""
    try:
        # Всегда используем CP866 для надежности
        codepage = 'CP866'

        # Получаем данные чека
        receipt_response = get_receipt_data(order_id)
        if isinstance(receipt_response, Response) and receipt_response.status_code != 200:
            return receipt_response

        receipt_data = receipt_response.data
        formatted_receipt = format_receipt(receipt_data, codepage)

        # Преобразуем бинарные данные в строку для передачи через API
        # Используем base64 для кодирования бинарных данных
        import base64
        encoded_receipt = base64.b64encode(formatted_receipt).decode('ascii')

        return Response({
            'receipt_text': encoded_receipt,
            'is_binary': True,  # Флаг, указывающий, что данные закодированы в base64
            'printer_settings': {
                'codepage': 'CP866',
                'chars_per_line': 48,
                'paper_width': 72,
                'cut_paper': True
            }
        })

    except Exception as e:
        return Response({'error': str(e)}, status=500)

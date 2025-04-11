from django.contrib.admin.views.decorators import staff_member_required
from shop.models import Order, OrderDish
from django.utils import timezone
from django.db.models import Sum, Count, F, Q
import datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from django.conf import settings
from django.db.models import Prefetch
from django.views.generic import TemplateView
from delivery_contacts.models import Courier, Restaurant
from django.http import HttpResponseRedirect, JsonResponse
from shop.admin_reports import get_report_data
from django.views import View
from django.shortcuts import get_object_or_404
from django.urls import reverse
import uuid
from datetime import datetime, timedelta

import logging.config

logger = logging.getLogger(__name__)


STANDARD_HEIGHT_ITEMS = 6  # Standard height is based on 6 items
# When using DOUBLE_BOTH, the actual characters per line is reduced
NORMAL_LINE_WIDTH = 48  # Maximum characters per line for 72mm paper
DOUBLE_LINE_WIDTH = 24  # When using double width, line width is halved


@staff_member_required
def sales_data(request):
    """Отчет по продажам за последний месяц на начальной странице.
    Разделяет типы заказов с сайта/ботоа.
    Для админов ресторанов показывается статистика их ресторана. Для суперюзера полная статистика."""
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    date_range = [(last_30_days + timedelta(days=i)) for i in range(31)]

    def fill_missing_dates(queryset, date_range):
        data_dict = {entry['day']: entry['total'] for entry in queryset}
        filled_data = [{'day': day, 'total': data_dict.get(day, 0)} for day in date_range]
        return filled_data

    def fill_missing_order_dates(queryset, date_range):
        data_dict = {entry['day']: entry['total_orders'] for entry in queryset}
        filled_data = [{'day': day, 'total_orders': data_dict.get(day, 0)} for day in date_range]
        return filled_data

    # Добавляем фильтр для исключения заказов со статусом "CND"
    not_canceled_filter = ~Q(status='CND')

    restaurant_title = None
    if not request.user.is_superuser:
        # Для DateField не требуется timezone.make_aware
        base_filter_ = Q(execution_date__gte=last_30_days) & not_canceled_filter
        restaurant = request.user.restaurant
        restaurant_title = str(restaurant)
        rest_filter = Q(restaurant=restaurant.id)
        base_filter = base_filter_ & rest_filter
    else:
        # Для DateField не требуется timezone.make_aware
        base_filter = Q(execution_date__gte=last_30_days) & not_canceled_filter

    web_filter = Q(source='4')
    bot_filter = Q(source='3')

    base_filter_q = base_filter
    base_web_filter_q = base_filter & web_filter
    base_bot_filter_q = base_filter & bot_filter

    # Запросы для подсчета общих продаж по дням
    total_sales_qs = Order.objects.filter(
            base_filter_q
        ).values('execution_date').annotate(
            day=F('execution_date'),  # Если execution_date это DateField
            total=Sum('final_amount_with_shipping')
        ).order_by('day')
    total_sales = fill_missing_dates(total_sales_qs, date_range)

    # Запросы для подсчета продаж с сайта (source='4') по дням
    site_sales_qs = Order.objects.filter(
            base_web_filter_q
        ).values('execution_date').annotate(
            day=F('execution_date'),
            total=Sum('final_amount_with_shipping')
        ).order_by('day')
    site_sales = fill_missing_dates(site_sales_qs, date_range)

    # Запросы для подсчета продаж с бота (source='3') по дням
    bot_sales_qs = Order.objects.filter(
            base_bot_filter_q
        ).values('execution_date').annotate(
            day=F('execution_date'),
            total=Sum('final_amount_with_shipping')
        ).order_by('day')
    bot_sales = fill_missing_dates(bot_sales_qs, date_range)

    # Запросы для подсчета общего количества заказов по дням
    total_orders_qs = Order.objects.filter(
            base_filter_q
        ).values('execution_date').annotate(
            day=F('execution_date'),
            total_orders=Count('id')
        ).order_by('day')
    total_orders = fill_missing_order_dates(total_orders_qs, date_range)

    # Запросы для подсчета количества заказов с сайта (source='4') по дням
    site_orders_qs = Order.objects.filter(
            base_web_filter_q
        ).values('execution_date').annotate(
            day=F('execution_date'),
            total_orders=Count('id')
        ).order_by('day')
    site_orders = fill_missing_order_dates(site_orders_qs, date_range)

    # Запросы для подсчета количества заказов с бота (source='3') по дням
    bot_orders_qs = Order.objects.filter(
            base_bot_filter_q
        ).values('execution_date').annotate(
            day=F('execution_date'),
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
            item['day'] = datetime.combine(
                item['day'],
                datetime.min.time())
    data['restaurant'] = restaurant_title
    return JsonResponse(data)


# ------------------------ ПЕЧАТЬ ЧЕКОВ ----------------------------

def transliterate_serbian_to_russian(text):
    """
    Заменяет сербские символы на их ближайшие русские эквиваленты
    для корректного отображения в CP866
    """
    if text is None:
        return ""

    serbian_to_russian = {
        # Сербская кириллица -> Русская кириллица
        'ђ': 'дж', 'Ђ': 'ДЖ',
        'ј': 'й', 'Ј': 'Й',
        'љ': 'ль', 'Љ': 'ЛЬ',
        'њ': 'нь', 'Њ': 'НЬ',
        'ћ': 'ч', 'Ћ': 'Ч',
        'џ': 'дж', 'Џ': 'ДЖ',

        # Сербская латиница -> Русская кириллица
        'đ': 'дж', 'Đ': 'ДЖ',
        'j': 'й', 'J': 'Й',
        'lj': 'ль', 'Lj': 'ЛЬ', 'LJ': 'ЛЬ',
        'nj': 'нь', 'Nj': 'НЬ', 'NJ': 'НЬ',
        'ć': 'ч', 'Ć': 'Ч',
        'č': 'ч', 'Č': 'Ч',
        'dž': 'дж', 'Dž': 'ДЖ', 'DŽ': 'ДЖ',
        'š': 'ш', 'Š': 'Ш',
        'ž': 'ж', 'Ž': 'Ж',
    }

    for serbian, russian in serbian_to_russian.items():
        text = text.replace(serbian, russian)

    return text


def encode_safely(text, encoding='cp866'):
    """
    Безопасное кодирование текста с заменой проблемных символов на ?
    """
    if text is None:
        return b''

    # Сначала транслитерация
    transliterated_text = transliterate_serbian_to_russian(text)

    # Затем безопасное кодирование
    try:
        return transliterated_text.encode(encoding, errors='replace')
    except Exception:
        # В случае непредвиденных ошибок возвращаем текст с ? вместо проблемных символов
        result = bytearray()
        for char in transliterated_text:
            try:
                result.extend(char.encode(encoding))
            except UnicodeEncodeError:
                result.extend(b'?')
        return bytes(result)


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
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return Response({'error': str(e), 'details': error_details}, status=500)


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
    receipt.extend(encode_safely(str(receipt_data['order_number']), codepage))
    receipt.extend(cmd.NORMAL_SIZE)
    receipt.extend(cmd.BOLD_OFF)
    receipt.extend(cmd.LF)
    receipt.extend(cmd.LF)

    # Menu items - left aligned
    receipt.extend(cmd.ALIGN_LEFT)
    receipt.extend(cmd.DOUBLE_BOTH)     #размер для блюд
    for item in receipt_data['items']:
        name = item['name'].upper()
        qty = f"x {item['quantity']}"  # Format quantity with 'x ' prefix

        # Calculate spaces needed - remember we're in double width mode
        # so we need to account for the reduced character width
        max_name_length = DOUBLE_LINE_WIDTH - len(qty) - 1  # Leave 1 space between name and qty
        if len(name) > max_name_length:
            # If name is too long, truncate it
            name = name[:max_name_length-3] + "..."

        # Calculate spaces needed
        spaces_needed = DOUBLE_LINE_WIDTH - len(name) - len(qty)
        spaces = ' ' * max(spaces_needed, 1)  # At least one space

        line = name + spaces + qty
        receipt.extend(encode_safely(line, codepage))
        receipt.extend(cmd.CRLF)

    receipt.extend(cmd.NORMAL_SIZE)
    receipt.extend(cmd.LF)

    # Service info - left aligned
    receipt.extend(cmd.ALIGN_LEFT)
    service_text = f"приборы - {receipt_data['persons_qty']} шт."
    receipt.extend(encode_safely(service_text, codepage))
    receipt.extend(cmd.CRLF)

    # Address
    if 'customer' in receipt_data and receipt_data['customer'].get('address'):
        address_text = receipt_data['customer']['address']
        receipt.extend(encode_safely(address_text, codepage))
        receipt.extend(cmd.CRLF)

    # Partner info if exists - right aligned
    if receipt_data['source_data']:
        receipt.extend(cmd.ALIGN_RIGHT)
        receipt.extend(cmd.DOUBLE_WIDTH)  # Увеличенный размер для источника
        receipt.extend(cmd.BOLD_ON)
        source_text = receipt_data['source_data']
        if len(source_text) > DOUBLE_LINE_WIDTH:
            source_text = source_text[-DOUBLE_LINE_WIDTH:]
        receipt.extend(encode_safely(source_text, codepage))
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

        # Проверка на наличие важных полей для предотвращения ошибок
        if not receipt_data:
            return Response({'error': 'No receipt data available'}, status=400)

        if 'order_number' not in receipt_data:
            receipt_data['order_number'] = f"####"

        if 'items' not in receipt_data or not isinstance(receipt_data['items'], list):
            receipt_data['items'] = []

        if 'persons_qty' not in receipt_data:
            receipt_data['persons_qty'] = 1

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
        import traceback
        error_details = traceback.format_exc()
        return Response({'error': str(e), 'details': error_details}, status=500)



# ------------------------ ОТЧЕТ СУПЕРАДМИНА ----------------------------


class AdminReportView(TemplateView):
    template_name = 'admin/superadmin_report.html'

    @method_decorator(staff_member_required)
    def dispatch(self, request, *args, **kwargs):
        # Check if user is superuser
        if not request.user.is_superuser:
            return HttpResponseRedirect('/admin/shop/order/')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get date range from request parameters
        start_date, end_date = self.get_date_range()

        # Get data for reports
        context['restaurant_data'] = self.get_restaurant_data(start_date, end_date)

        # Add date filtering context
        context['report_date'] = self.report_date

        return context

    def get_date_range(self):
        """Get date range from request parameters or use default (today)"""
        today = timezone.now().date()

        report_date_str = self.request.GET.get('report_date')

        # Parse dates if provided
        if report_date_str:
            try:
                report_date = datetime.strptime(report_date_str, '%Y-%m-%d').date()
            except ValueError:
                report_date = today
        else:
            report_date = today

        # Create start and end datetime for the same day
        start_datetime = datetime.combine(report_date, datetime.min.time())
        end_datetime = datetime.combine(report_date + timedelta(days=1), datetime.min.time())

        # Make aware if using timezone
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)

        # Save report date for template
        self.report_date = report_date_str or report_date.strftime('%Y-%m-%d')

        return start_datetime, end_datetime

    def get_restaurant_data(self, start_date, end_date):
        """Get restaurant-related data aggregated by city and restaurant"""
        orders = Order.objects.filter(
                    execution_date__gte=start_date,
                    execution_date__lt=end_date,
                ).exclude(
                    status='CND'
                ).select_related(
                        'delivery',
                        'delivery_zone',
                        'courier')

        # Prepare result structure
        restaurants_data = {}

        # Process all cities
        for city_code, city_name in settings.CITY_CHOICES:
            city_orders = orders.filter(city=city_code)

            # Skip cities with no orders
            if not city_orders.exists():
                continue

            # Initialize city data
            city_data = {
                'name': city_name,
                'restaurants': {}
            }

            # Get all restaurants in this city
            restaurants = Restaurant.objects.filter(city=city_code)

            # Process each restaurant
            for restaurant in restaurants:
                restaurant_orders = city_orders.filter(restaurant=restaurant)

                # Skip restaurants with no orders
                if not restaurant_orders.exists():
                    continue

                restaurant_data_item = get_report_data(restaurant_orders)
                # Add restaurant data to the city
                city_data['restaurants'][restaurant.id] = restaurant_data_item

            # Only add cities with restaurants that have data
            if city_data['restaurants']:
                restaurants_data[city_code] = city_data

        return restaurants_data


# ------------------------ ПОВТОР ЗАКАЗА ----------------------------

@method_decorator(staff_member_required, name='dispatch')
class RepeatOrderView(View):
    """
    Представление для инициирования повтора заказа
    """
    def get(self, request, order_id):
        try:
            # Получаем заказ по ID
            order = get_object_or_404(Order, pk=order_id)

            # Проверяем права доступа
            if not request.user.is_superuser and getattr(request.user, 'restaurant', None) != order.restaurant:
                logger.warning(f"Попытка повтора заказа {order_id} пользователем {request.user} без прав доступа")
                return JsonResponse({'error': 'У вас нет прав для повтора этого заказа'}, status=403)

            # Получаем блюда заказа
            order_dishes = OrderDish.objects.filter(order=order).select_related('dish')
            dishes = []

            for order_dish in order_dishes:
                dishes.append({
                    'dish_id': order_dish.dish.id,
                    'quantity': order_dish.quantity,
                })

            # Формируем данные для формы нового заказа
            data = {
                'order_type': 'D' if order.delivery.type == 'delivery' else 'T',
                'city': order.city,
                'recipient_name': order.recipient_name,
                'recipient_phone': order.recipient_phone,
                'recipient_address': order.recipient_address,
                # 'recipient_address_comment': order.recipient_address_comment,
                'coordinates': order.coordinates,
                'address_comment': order.address_comment,
                'payment_type': order.payment_type,
                'invoice': order.invoice,
                'comment': order.comment,
                'dishes': dishes,
                'original_order_id': order.id,
                'timestamp': timezone.now().isoformat()
                # discount / manual_discount / restaurant /
            }

            # Генерируем уникальный токен для операции
            repeat_token = str(uuid.uuid4())

            # Сохраняем данные в сессию с ограниченным временем жизни
            request.session[f'repeat_order_{repeat_token}'] = data

            # Записываем информацию о действии в лог
            logger.info(f"Заказ {order_id} подготовлен для повтора пользователем {request.user.username}, токен: {repeat_token}")

            # Перенаправляем на страницу создания заказа с токеном
            return HttpResponseRedirect(reverse('admin:shop_order_add') + f'?repeat_token={repeat_token}')

        except Exception as e:
            logger.error(f"Ошибка при подготовке повтора заказа {order_id}: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(staff_member_required, name='dispatch')
class PrepareRepeatOrderView(View):
    """
    API для получения данных повторяемого заказа по токену
    """
    def get(self, request):
        try:
            # Получаем токен из параметров запроса
            token = request.GET.get('token')
            if not token:
                return JsonResponse({'error': 'Отсутствует токен повтора заказа'}, status=400)

            # Формируем ключ сессии
            session_key = f'repeat_order_{token}'

            # Получаем данные из сессии
            order_data = request.session.get(session_key)

            if not order_data:
                logger.warning(f"Попытка использования недействительного или истекшего токена: {token}")
                return JsonResponse({
                    'error': 'Недействительный или истекший токен повтора заказа',
                    'valid': False
                }, status=400)

            # Проверяем срок действия токена (15 минут)
            from datetime import datetime, timedelta
            from django.utils import timezone

            timestamp = datetime.fromisoformat(order_data['timestamp'])
            if timezone.now() - timestamp > timedelta(minutes=15):
                # Удаляем просроченные данные
                del request.session[session_key]
                request.session.modified = True

                logger.warning(f"Попытка использования истекшего токена: {token}")
                return JsonResponse({
                    'error': 'Срок действия токена истек. Пожалуйста, повторите операцию.',
                    'valid': False
                }, status=400)

            # Удаляем данные из сессии после первого использования
            del request.session[session_key]
            request.session.modified = True

            logger.info(f"Токен {token} успешно использован для повтора заказа пользователем {request.user.username}")

            # Возвращаем данные для заполнения формы
            return JsonResponse({
                'valid': True,
                'data': order_data
            })

        except Exception as e:
            logger.error(f"Ошибка при обработке токена повтора заказа: {str(e)}")
            return JsonResponse({'error': str(e), 'valid': False}, status=500)

import datetime
from copy import copy
from datetime import datetime, timedelta
from django.template.response import TemplateResponse
from django.conf import settings
from django.contrib import messages, admin
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, F, Q, Prefetch
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from catalog.forms import DishPricesUploadForm
from catalog.admin_utils.excell import (export_prices_to_excel,
                                        import_prices_from_excel,
                                        ExcelImportError)

from delivery_contacts.models import Courier, Restaurant
from shop.admin_reports import get_report_data
from shop.models import Order, OrderDish
from shop.reports import excel as xls_reports
from shop.reports.report_page_forms import AdminXlsReportForm


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
        logger.info('\nRECEIPT_DATA printed:\n%s', receipt_data)
        return Response(receipt_data)
    except Order.DoesNotExist:
        logger.error('Order %s not found.', order_id)
        return Response({'error': 'Order not found'}, status=404)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error('ORDER %s RECEIPT PRINTING FAILED. \nError: %s \nOrder: %s',
                     order_id, str(e), order)
        return Response({'error': str(e), 'details': error_details},
                        status=500)


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
        if not request.user.has_perm("shop.view_superuser_report"):
            return HttpResponseRedirect('/admin/shop/order/')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get date range from request parameters
        start_date, end_date = self.get_date_range()

        # Get data for reports
        context['restaurant_data'] = self.get_restaurant_data(start_date,
                                                              end_date)

        # Add date filtering context
        context['start_date'] = self.start_date
        context['end_date'] = self.end_date

        return context

    def get_date_range(self):
        """Get date range from request parameters or use default (today)"""
        today = timezone.now().date()

        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')

        if not start_date_str:
            # не задан день или начало периода
            # Create start and end datetime for the same day
            start_date = today
            end_date = today + timedelta(days=1)

        if start_date_str:
            try:
                if end_date_str in ['', None]:
                    start_date = datetime.strptime(start_date_str,
                                                   '%Y-%m-%d').date()
                    end_date = start_date + timedelta(days=1)

                else:
                    start_date = datetime.strptime(start_date_str,
                                                   '%Y-%m-%d').date()
                    end_date = datetime.strptime(end_date_str,
                                                 '%Y-%m-%d').date()
            except ValueError:
                start_date = today
                end_date = today + timedelta(days=1)

        # Save report date for template
        self.start_date = start_date.strftime('%Y-%m-%d')
        self.end_date = end_date.strftime('%Y-%m-%d')

        return start_date, end_date

    def get_restaurant_data(self, start_date, end_date):
        """Get restaurant-related data aggregated by city and restaurant"""
        user = self.request.user

        # 1. Сначала определяем доступные рестораны
        if user.is_superuser:
            restaurants = Restaurant.objects.all()
        else:
            user_restaurant = getattr(user, 'restaurant', None)
            if not user_restaurant:
                return {}

            restaurants = Restaurant.objects.filter(pk=user_restaurant.pk)

        # 2. Из них получаем доступные города
        allowed_city_codes = list(
            restaurants.values_list('city', flat=True).distinct()
        )
        city_name_map = dict(settings.CITY_CHOICES)

        if not allowed_city_codes:
            return {}

        # 3. Сразу формируем orders только по доступным ресторанам/городам
        orders = (
            Order.objects.filter(
                execution_date__gte=start_date,
                execution_date__lt=end_date,
                restaurant__in=restaurants,
            )
            .exclude(status='CND')
            .select_related('delivery', 'delivery_zone', 'courier', 'restaurant')
        )

        restaurants_data = {}

        # 4. Идём только по разрешённым городам
        for city_code in allowed_city_codes:
            city_orders = orders.filter(city=city_code)

            if not city_orders.exists():
                continue

            city_data = {
                'name': city_name_map.get(city_code, city_code),
                'restaurants': {}
            }

            city_restaurants = restaurants.filter(city=city_code)

            for restaurant in city_restaurants:
                restaurant_orders = city_orders.filter(restaurant=restaurant)

                if not restaurant_orders.exists():
                    continue

                city_data['restaurants'][restaurant.id] = {
                    "name": restaurant.address,
                    "data": get_report_data(restaurant_orders)
                }

            if city_data['restaurants']:
                restaurants_data[city_code] = city_data

        return restaurants_data


@method_decorator(staff_member_required, name='dispatch')
class AdminXlsReportView(View):
    template_name = 'admin/xls_report.html'
    form_class = AdminXlsReportForm
    page_title = 'Скачать отчет по заказам'

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial={'period': AdminXlsReportForm.PERIOD_TODAY})
        return TemplateResponse(request, self.template_name, self._get_context(request, form))

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if not form.is_valid():
            return TemplateResponse(request, self.template_name, self._get_context(request, form))

        export_request = self._build_export_request(request, form.cleaned_data)
        report_type = form.cleaned_data['report_type']

        if report_type == AdminXlsReportForm.REPORT_FULL:
            return xls_reports.export_full_orders_to_excel(None, export_request, None)
        return xls_reports.export_orders_to_excel(None, export_request, None)

    def _get_context(self, request, form):
        from shop.models import Order
        return {
            **admin.site.each_context(request),
            'opts': Order._meta,
            'form': form,
            'back_url': reverse('admin:shop_order_changelist'),
        }

    def _build_export_request(self, request, cleaned_data):
        export_request = copy(request)
        params = request.GET.copy()
        params.clear()

        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        period = cleaned_data.get('period')

        if date_from and date_to:
            params['execution_date__range__gte'] = date_from.strftime('%d.%m.%Y')
            params['execution_date__range__lte'] = date_to.strftime('%d.%m.%Y')
        else:
            params['order_period'] = period

        export_request.GET = params
        return export_request


class AdminDishPriceXlsDownloadView(View):

    @method_decorator(staff_member_required)
    def get(self, request):
        return export_prices_to_excel(request)


class AdminDishPriceXlsUploadView(View):
    @method_decorator(staff_member_required)
    def get(self, request):
        form = DishPricesUploadForm()
        return render(
            request,
            "catalog/dish/upload_prices.html",
            {"form": form},
        )

    @method_decorator(staff_member_required)
    def post(self, request):
        form = DishPricesUploadForm(request.POST, request.FILES)

        if not form.is_valid():
            return render(
                request,
                "catalog/dish/upload_prices.html",
                {"form": form},
            )

        try:
            result = import_prices_from_excel(form.cleaned_data["file"])

            messages.success(
                request,
                (
                    f"Цены загружены. "
                    f"Сайт: создано {result.created_site}, обновлено {result.updated_site}. "
                    f"Партнёры: создано {result.created_partner}, обновлено {result.updated_partner}. "
                    f"Пропущено строк: {result.skipped}."
                ),
            )

            # Показываем построчные ошибки (битые ячейки, неполные данные и т.п.),
            # если они есть — раньше такие строки либо валили весь импорт,
            # либо молча игнорировались.
            if result.errors:
                for err in result.errors[:10]:
                    messages.warning(
                        request,
                        f"Строка {err.row} (артикул {err.article}, город {err.city}): {err.message}",
                    )
                if len(result.errors) > 10:
                    messages.warning(
                        request,
                        f"...и ещё {len(result.errors) - 10} строк с ошибками.",
                    )

        except ExcelImportError as e:
            # Критическая ошибка структуры файла (неизвестный город, нет нужных колонок) —
            # импорт не выполнялся вовсе.
            messages.error(request, f"Ошибка загрузки цен: {e}")
        except Exception as e:
            messages.error(request, f"Непредвиденная ошибка при загрузке цен: {e}")

        return redirect("admin:catalog_dish_changelist")

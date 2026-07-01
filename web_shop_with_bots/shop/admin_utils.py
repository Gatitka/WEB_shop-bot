"""Функции, необходимые для отображения админки"""

from shop.models import Order
from shop.reports.summary import get_report_data
from delivery_contacts.models import DeliveryZone
from delivery_contacts.utils import get_google_api_key
from django.utils import timezone
from django.conf import settings
from catalog.models import Category, DishCategory
import re
from django.utils.html import format_html
from shop.utils import get_flag
from decimal import Decimal, ROUND_HALF_UP


def my_get_object(model, object_id, source=None):
    # Определяем поля для использования в запросе
    select_related_fields = [
        'restaurant',
    ]
    prefetch_related_fields = [
        'orderdishes__dish__translations',
        # 'orderdishes__dish__article',
    ]
    if source is None:
        select_related_fields += [
            'delivery',
            'delivery_zone',
            'msngr_account',
            'courier',
            'promocode',
            'courier',
        ]
        prefetch_related_fields += [
            'user',
            'user__messenger_account'
        ]

    # Создаем запрос для конкретного объекта с нужными связями
    try:
        order = model.objects.select_related(
                    *select_related_fields
                ).prefetch_related(
                    *prefetch_related_fields
                ).get(pk=int(object_id))
        return order
    except model.DoesNotExist:
        return None


def my_get_queryset(request, qs):
    if request.user.is_superuser:
        return qs
    view = request.GET.get('view', None)
    e = request.GET.get('e', None)
    if view == 'all_orders' or e == '1':
        return qs
    restaurant = request.user.restaurant
    if restaurant:
        qs = qs.filter(restaurant=restaurant)
        return qs


def get_menu_data():
    """
    Формирует оптимизированные данные меню: словарь категорий и словарь блюд.

    Returns:
        tuple: (categories, dishes) где:
            - categories: словарь категорий {id: {Image, Name, Dishes[]}}
            - dishes: словарь блюд {id: {Name, Image, Price[]}}
    """
    # Язык, который мы хотим использовать
    language_code = 'ru'

    # Получаем активные категории с переводами отсортированные
    # по приоритетности, чтобы Допы были в конце списка
    categories_queryset = Category.objects.filter(
            is_active=True
        ).prefetch_related(
            'translations'
        ).order_by('priority')

    # Подгружаем связи между категориями и блюдами с предзагрузкой данных о блюдах
    dish_categories = DishCategory.objects.select_related('dish', 'category').prefetch_related(
        'dish__translations'
    )

    # Создаем результирующие словари
    categories = {}
    dishes = {}

    # Заполняем словарь категорий
    for category in categories_queryset:
        # Пытаемся получить перевод на русском
        category_name = None
        for translation in category.translations.all():
            if translation.language_code == language_code and translation.name:
                category_name = translation.name
                break

        # Если русского перевода нет, берем первый доступный
        if not category_name and category.translations.exists():
            category_name = category.translations.first().name

        # Если вообще нет переводов, используем ID
        if not category_name:
            category_name = f"Категория {category.id}"

        categories[category.id] = {
            "Image": "",  # У категорий нет изображений в модели
            "Name": category_name,
            "Dishes": []  # Заполним позже
        }

    # Заполняем словарь блюд и связи категория-блюдо
    for relation in dish_categories:
        dish = relation.dish
        category_id = relation.category_id

        # Пропускаем, если категория не активна
        if category_id not in categories:
            continue

        # Добавляем ID блюда в список блюд категории
        categories[category_id]["Dishes"].append(dish.article)

        # Если блюдо уже добавлено в словарь блюд, пропускаем
        if dish.article in dishes:
            continue

        # Пытаемся получить перевод на русском
        dish_name = None
        for translation in dish.translations.all():
            if translation.language_code == language_code and translation.short_name:
                dish_name = translation.short_name
                break

        # Если русского перевода нет, берем первый доступный
        if not dish_name and dish.translations.exists():
            dish_name = dish.translations.first().short_name

        # Если вообще нет переводов, используем артикул
        if not dish_name:
            dish_name = f"Блюдо {dish.article}"

        dishes[dish.article] = {
            "Name": dish_name,
            "Image": dish.image.url if dish.image else "",
            "Price": [
                float(dish.final_price),     # основная цена
                float(dish.final_price_p1),  # цена для партнера P1
                float(dish.final_price_p2)   # цена для партнера P2
            ],
            "Utensils": dish.utensils
        }

    # Удаляем категории без блюд
    categories = {k: v for k, v in categories.items() if v["Dishes"]}

    return categories, dishes


def get_delivery_zones():
    """
    Формирует оптимизированные данные по зонам доставки.

    Returns:
        - delivery_zones: словарь зон доставки {id: {name, delivery_cost, is_promo, promo_min_order_amount}}

    """
    # Получаем активные категории с переводами
    delivery_zones_list = DeliveryZone.objects.all()

    # Создаем результирующие словари
    delivery_zones = {}

    # Заполняем словарь
    for delivery_zone in delivery_zones_list:
        delivery_zones[delivery_zone.id] = {
            "name": delivery_zone.name,
            "delivery_cost": delivery_zone.delivery_cost,
            "is_promo": delivery_zone.is_promo,
            "promo_min_order_amount": delivery_zone.promo_min_order_amount,
        }

    return delivery_zones


def get_addchange_extra_context(request, extra_context, type=None, source=None):
    """ Формирует extra_conext в форму создания заказа.
        Пробрасывает GOOGLE_API_KEY, menu, delivery_zones."""
    extra_context["categories"], extra_context["dishes"] = get_menu_data()

    if type == 'all':
        extra_context["GOOGLE_API_KEY"] = get_google_api_key()
        extra_context["delivery_zones"] = get_delivery_zones()
    return extra_context


def get_changelist_extra_context(request, extra_context, source=None):
    """ Формирует extra_conext в форму списка заказов, добавляя данные
    для ежедневного отчета."""
    extra_context = extra_context or {}
    view = request.GET.get('view', None)
    e = request.GET.get('e', None)

    today = timezone.now().date()

    filters = {
               'execution_date': today,
                }
    if source:
        filters['source'] = source

    if request.user.is_superuser or view == 'all_orders' or e == '1':
        # собираем данные по заказам:
        # если есть сорс, то определнный тип заказа во всех ресторанах
        # если нет сорса, то все типы заказов во всех ресторанах
        title = "Заказы всех ресторанов"

    else:
        # собираем данные по ресторану
        restaurant = request.user.restaurant
        filters['restaurant'] = restaurant
        title = f"Заказы ресторана: {restaurant.city}/{restaurant.address}"

        today_orders = Order.objects.filter(
                    **filters
                ).exclude(
                    status='CND'
                ).select_related(
                    'delivery',
                    'delivery_zone',
                    'courier')
        extra_context.update(get_report_data(today_orders))

    extra_context['title'] = title

    return extra_context


# --------------------- ФОРМАТИРОВАНИЕ ПОЛЕЙ СПИСКА ЗАКАЗОВ -------------------------


def get_custom_order_number(obj):
    """
    В форме списка заказов формирует колонку №, добавляя:
    - скрытые данные о создании и времени выдачи (если в будущем).
    - кнопки печати чека и копировани язаказа
    """
    # return custom_order_number(obj)
    # return obj.order_number
    # Формируем номер заказа
    order_number = obj.order_number
    tooltip_text = f"Создан: {obj.created.astimezone(timezone.get_current_timezone()).strftime('%d.%m.%Y %H:%M ')}"
    if hasattr(obj, 'delivery_time') and obj.delivery_time:
        tooltip_text += f"\nВремя выдачи: {obj.delivery_time.astimezone(timezone.get_current_timezone()).strftime('%d.%m.%Y %H:%M')}"

    # Добавляем кнопку печати под номером
    buttons = format_html(
        '<div class="order-action-buttons" style="display: flex; justify-content: space-between; margin-top:5px;">'
        '<button type="button" class="print-button" data-id="{}" title="Распечатать чек" style="background-color: #fff; border: 1px solid #ccc; padding: 3px 8px; border-radius: 3px; color: #555; cursor: pointer;">'
        '<span style="font-size: 12px;">🖨</span></button>'
        '</div>',
        obj.id, obj.id
    )
    # Объединяем номер и кнопку с переносом строки между ними
    return format_html(
        '<span title="{}">{}</span><br>{}',
        tooltip_text,
        order_number,
        buttons
    )


def get_warning(obj):
    """
    В форме списка заказов формирует колонку !, добавляя !!!
    в случаях ошибок/неполноты данных в заказе.
    """
    help_text = []
    if obj.delivery.type == 'delivery':
        if obj.delivery_zone.name == 'уточнить':
            help_text.append("Уточнить зону доставки.\n")

        if obj.courier is None:
            help_text.append("Не назначен курьер.\n")

        address = obj.recipient_address
        if address not in ['', None] and not re.search(r'\d+', address):
            help_text.append('Нет дома, перепроверить стоимость доставки\n')

    if obj.source not in settings.PARTNERS_LIST and obj.payment_type is None:
        help_text.append("Тип оплаты не определен.\n")

    if obj.process_comment:
        help_text.append("Ошибки в сохранении заказа.\n")

    help_text = "".join(help_text)

    if help_text != '':
        # Возвращение HTML с подсказкой
        return format_html(
            '<span style="color:red;" title="{}">!!!</span>', help_text)
    else:
        return ''


def get_info(obj):
    """
    В форме списка заказов формирует колонку АДРЕС.
    В случае партнерского заказа показывает его название.
    В случае внутреннего заказа показывает "самовывоз" или адрес доставки.
    """
    source = obj.source
    if source in ['1', '2', '3', '4']:
        # если не через партнеров, а из наших источников заказ
        if obj.delivery.type == 'delivery':
            address = obj.recipient_address

            if address in ['', None]:
                return '❓нет адреса доставки'

            if obj.delivery_zone.name == 'уточнить':
                address = format_html('<span style="color:red;">{}</span>',
                                      address)
            return address

        elif obj.delivery.type == 'takeaway':
            return 'самовывоз'
        elif obj.delivery.type == 'restaurant':
            return 'ресторан'
    else:
        return obj.get_source_display()


# def get_custom_total(obj):
#     if (obj.process_comment or
#             obj.delivery_zone and obj.delivery_zone.name == 'уточнить'):
#         return format_html(
#             '<span style="color:red;">{}</span>',
#             obj.final_amount_with_shipping)
#     return obj.final_amount_with_shipping

def get_custom_total(obj):
    # красный стиль включается, если заказ с вопросами
    style = ''
    if (obj.process_comment or (obj.delivery_zone and obj.delivery_zone.name == 'уточнить')):
        style = 'color:red;'

    # считаем tooltip, если есть скидка и есть база для процента
    tooltip = ''
    if obj.discount_amount and obj.discount_amount != 0 and obj.amount_with_shipping:
        # процент от суммы "с учетом доставки"
        percent = (Decimal(obj.discount_amount) / Decimal(obj.amount_with_shipping)) * Decimal('100')
        percent = percent.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        tooltip = f'Скидка: {obj.discount_amount} DIN ({percent}%)'

    # если есть tooltip — кладём его в title, иначе просто значение
    if tooltip:
        return format_html(
            '<span style="{}" title="{}">{}<br>🔻</span>',
            style,
            tooltip,
            obj.final_amount_with_shipping,
            "%"
        )
    return format_html(
        '<span style="{}">{}</span>',
        style,
        obj.final_amount_with_shipping,
    )


def get_note(obj):
    """
    В форме списка заказов формирует колонку ПРИМЕЧАНИЕ.
    В случае партнерского заказа показывает его id в системе источнике.
    """
    # if obj.source in ['3'] + settings.PARTNERS_LIST:   при ботобот наглядно проверялось есть ли ID заказа
    if obj.source in settings.PARTNERS_LIST:
        source = obj.get_source_display()
        source_id = f'{obj.source_id}' if obj.source_id is not None else ''
        if obj.source_id:
            if source == 'TM_Bot':
                source = f"{source}{obj.orders_bot_id}"
                return format_html(
                    '{}<br>{}',
                    source, source_id)

            return source_id
        else:
            return '❓нет ID'
    return ''


def get_custom_delivery_cost(obj):
    if obj.delivery_zone:
        if obj.delivery_zone.name in ['по запросу']:
            return obj.delivery_cost
        elif obj.delivery_zone.name in ['уточнить']:
            return format_html('<span style="color:red;">{}</span>',
                               obj.delivery_cost)
        else:
            return obj.delivery_zone.delivery_cost
    return ''


def get_contacts(obj):
    lang = get_flag(obj)
    name = format_html('{} {}',
                       lang,
                       obj.recipient_name if obj.recipient_name else '')
    msngr_link = ''
    phone = obj.recipient_phone if obj.recipient_phone else ''
    if obj.user:
        name = f'{lang}👤 {obj.recipient_name}'
        if obj.is_first_order:
            name = f'{lang}🥇👤 {obj.recipient_name}'
        if obj.user.messenger_account:
            if obj.user.messenger_account.msngr_link:
                msngr_link = format_html(obj.user.messenger_account.msngr_link)
            msngr_link = format_html("<span style='color:#888;'>"
                                     "Чат недоступен")
        else:
            msngr_link = format_html("<span style='color:#888;'>"
                                     "нет мессенджера")
    else:
        if obj.msngr_account:
            if obj.msngr_account.msngr_link:
                msngr_link = format_html(obj.msngr_account.msngr_link)
            msngr_link = format_html("<span style='color:#888;'>"
                                     "Чат недоступен")
        else:
            msngr_link = format_html("<span style='color:#888;'>"
                                     "нет мессенджера")

    return format_html('{}<br>{}<br>{}',
                       name,
                       phone,
                       msngr_link)

# --------------------- ФОРМАТИРОВАНИЕ ПОЛЕЙ В ДРУГИХ ФОРМАХ -----------------


def custom_source(obj):
    """
    Формируем колонку ИСТОЧНИК в clients / messenger_account.
    """
    # краткое название поля в list
    source_id = f'#{obj.source_id}' if obj.source_id is not None else ''
    source = obj.get_source_display()
    if source == "TM_Bot" and obj.orders_bot_id:
        source = f"{source}{obj.orders_bot_id}"
    if obj.status == 'WCO':
        return format_html(
            '<span style="color:green; font-weight:bold;">{}<br>{}</span>',
            source, source_id)

    return format_html('{}<br>{}', source, source_id)

from django.contrib import admin, messages
from django.core.files.base import ContentFile
from django.db.models import (Count, Sum, Value, DecimalField, Max,
                              OuterRef, Subquery)
from django.db.models.functions import Coalesce

from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django_summernote.widgets import SummernoteWidget
from django.urls import path
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from parler.admin import (TranslatableAdmin,
                          TranslatableModelForm)

from utils.utils import active_actions
from utils.admin_permissions import has_city_admin_permissions
from promos.models import (PrivatPromocode, Promocode, PromoNews,
                     PromoBroadcast, Campaign, Banner)
from promos.admin_configs.banner_fieldsets import (
    BANNER_ADD_FIELDSETS,
    BANNER_CHANGE_FIELDSETS,
)
from .tasks import (send_broadcast_task,
                    send_broadcast_test_task,
                    send_broadcast_test_task_singleflow)
from shop.models import Order
from catalog.models import Dish, Category

import json
import os
import logging

logger = logging.getLogger(__name__)


class PromoNewsForm(TranslatableModelForm):
    class Meta:
        model = PromoNews
        fields = '__all__'
        widgets = {
            'content': SummernoteWidget(),
        }


@admin.register(PromoNews)
class PromoNewsAdmin(TranslatableAdmin):

    def custom_title(self, obj):
        return format_html("<b>{}</b><br><br>slug: <i>{}</i>", obj.title, obj.slug)
    custom_title.short_description = "Название / Slug"

    """Настройки админ панели промо-новостей."""
    list_display = ['id', 'custom_title', 'is_active', 'city', 'created', 'admin_image_ru']
    readonly_fields = ('custom_title', 'admin_image_ru', 'created',
                       'admin_image_en', 'admin_image_sr_latn')
    actions = [*active_actions]
    search_fields = ('translations__title__icontains',
                     'translations__full_text__icontains')
    list_filter = ('is_active', 'city')
    list_display_links = ('custom_title',)

    form = PromoNewsForm

    class Media:
        css = {
            'all': ('my_admin/css/faq/faq.css',)
        }

    fieldsets = (
        ('Основное', {
            'fields': (
                ('created', 'is_active'),
                ('city',),
                ('slug')
            )
        }),
        ('Описание', {
            'fields': (
                ('title'),
                ('full_text'),
            )
        }),
        ('Изображения', {
            'fields': (
                ('image_ru', 'admin_image_ru'),
                ('image_en', 'admin_image_en'),
                ('image_sr_latn', 'admin_image_sr_latn'),
            )
        }),
    )

    # def get_queryset(self, request):
    #     return super().get_queryset(request).prefetch_related('translations')


# @admin.register(Promocode)
# class PromocodeAdmin(admin.ModelAdmin):
#     """Настройки админ панели промо-новостей."""
#     list_display = ['id', 'is_active', 'title_rus', 'code']
#     readonly_fields = ('id', 'created')
#     actions = [*active_actions]
#     search_fields = ('promocode', 'title_rus')
#     list_filter = ('is_active',)


# @admin.register(PrivatPromocode)
# class PrivatPromocodeAdmin(admin.ModelAdmin):
#     """Настройки админ панели промо-новостей."""
#     list_display = ('id', 'promocode', 'base_profile', 'is_active', 'is_used')
#     readonly_fields = ('created',)
#     actions = [*active_actions]
#     search_fields = ('promocode', 'base_profile')
#     list_filter = ('is_active', 'is_used')


@admin.register(PromoBroadcast)
class PromoBroadcastAdmin(admin.ModelAdmin):

    def report_link(self, obj):
        if obj.report_file:
            return format_html('<a href="{}" target="_blank">Скачать отчет</a>',
                               obj.report_file.url)
        return "—"
    report_link.short_description = "Отчет"

    list_display = (
        "title",
        "admin_photo",
        "city",
        "status",
        "sent_at",
        "progress_display",
        "delivered_display",
        "results_short",
    )
    list_filter = ("status", "bot__city")
    readonly_fields = (
        #"status",
        "admin_photo",
        "total_recipients",
        "processed_count",
        "delivered_display",
        "progress_display",
        "results_display",
        "created_at", "updated_at", "sent_at",
        "report_link"
    )

    change_form_template = "promos/promobroadcast/change_form.html"
    change_list_template = "promos/promobroadcast/change_list.html"

    class Media:
        js = ('my_admin/js/promos/promobroadcast/summernote_resize.js',)
        css = {
            'all': ('my_admin/css/faq/faq.css')
        }

    def get_form(self, request, obj=None, **kwargs):
        """Необходимо переписать поля summernote в форме, чтобы поменять
        главный сеттинг из settings.py."""
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['body'].widget = SummernoteWidget(attrs={
            'summernote': {
                'iframe': True,
                'toolbar': [
                    ['font', ['bold', 'italic', 'underline', 'clear']],
                    ['insert', ['link']],
                    ['view', ['codeview']],
                ],
                # 'height': 400,
                'width': '400px',
                'disableResizeEditor': False,
                'linkTargetBlank': False,  # Убирает чекбокс target="_blank"
                'dialogsInBody': True,
                'popover': {
                    'link': [
                        ['link', ['linkDialogShow', 'unlink']]
                    ]
                }
            }
        })
        return form

    def get_fieldsets(self, request, obj=None):
        # description = mark_safe("""
        #     <div class="help" style="padding:8px 12px;">
        #         <b>Как работает рассылка в Telegram</b><br><br>
        #         <b>Варианты отправки:</b><br>
        #         1. <b>Только картинка</b> — в рассылке указываем файл/URL картинки, поле текста можно оставить пустым.<br>
        #         2. <b>Картинка + текст</b> — текст отправляется как подпись (caption) к картинке.<br>
        #         3. <b>Только текст</b> — картинка не указана, отправляется обычное текстовое сообщение.<br><br>

        #         <b>Лимиты по длине текста:</b><br>
        #         • обычное текстовое сообщение — до <b>4096 символов</b>;<br>
        #         • подпись (caption) к картинке — до <b>1024 символов</b>.<br><br>

        #         <b>Что считается символом:</b><br>
        #         • буквы, цифры, пробелы;<br>
        #         • знаки препинания и спецсимволы;<br>
        #         • переводы строк (Enter);<br>
        #         • эмодзи 😊;<br>
        #         • теги разметки HTML/Markdown (например, &lt;b&gt;...&lt;/b&gt;) — они тоже входят в лимит, даже если не отображаются как текст.
        #     </div>
        # """)

        if obj is None:  # форма создания
            return (
                (None, {
                    # "description": description,
                    "fields": (
                        "status",
                        ("title", "bot"),
                        "body",
                        ("admin_photo", "image"),
                        # "disable_link_preview",
                        # "add_inline_keyboard",
                        # "add_reply_keyboard",
                    )
                }),
            )

        # форма редактирования
        return (
            (None, {
                "fields": (
                    ("status", "sent_at", ),
                    ("total_recipients", "delivered_display"),
                    ("progress_display", "processed_count"),
                    ("bot"),
                    "body",
                    ("admin_photo", "image"),
                    ("results_display", "report_link"),
                    ("created_at", "updated_at"),
                    # "add_inline_keyboard",
                    # "add_reply_keyboard",
                )
            }),
        )

    # 🔹 1) Ограничиваем список рассылок по городу для обычных админов
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user

        if user.is_superuser:
            return qs

        # предполагаю, что у WEBAccount есть city и role
        user_city = getattr(user, "city", None)
        user_role = getattr(user, "role", None)

        if user_role == "admin" and user_city:
            return qs.filter(bot__city=user_city)

        return qs.none()

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<int:pk>/send/",
                self.admin_site.admin_view(self.send_view),
                name="promos_promobroadcast_send",
            ),
        ]
        return my_urls + urls

    def send_view(self, request, pk):
        broadcast = self.get_object(request, pk)
        if not broadcast:
            messages.error(request, "Рассылка не найдена.")
            return redirect("..")

        send_broadcast_task.delay(broadcast.id)
        messages.success(
            request,
            "Задача на рассылку добавлена в очередь Celery. Отправка запущена.",
        )
        return redirect("..")

    def response_change(self, request, obj):
        """
        Переопределяем стандартный ответ после сохранения объекта.
        Смотрим, какая кнопка нажата.
        """
        if "_send_test" in request.POST:
            # объект уже сохранён к этому моменту
            logger.debug("Send test broadcast: %s.", obj)
            test_chat_id = obj.bot.admin_id
            if not test_chat_id:
                self.message_user(
                    request,
                    format_html(
                        "У выбранного бота не указан ID админа — тестовая рассылка не может быть отправлена.<br>"
                        "Пожалуйста, внесите ID админа и попробуйте снова."
                    ),
                    level=messages.ERROR
                )
                return HttpResponseRedirect(request.path)
            # send_broadcast_test_task.delay(obj.id)          # параллельное через celery
            send_broadcast_test_task_singleflow(obj.id)   # последовательное выполнение

            logger.debug("Tasked test broadcast: %s.", obj)
            self.message_user(
                request,
                "Тестовая отправка поставлена в очередь.",
                level=messages.INFO,
            )
            return HttpResponseRedirect(request.path)  # остаться на той же странице

        if "_send_all" in request.POST:
            logger.debug("Send broadcast to all users: %s.", obj)
            send_broadcast_task.delay(obj.id)
            self.message_user(
                request,
                "Рассылка всем пользователям поставлена в очередь.",
                level=messages.SUCCESS,
            )
            return HttpResponseRedirect(request.path)  # тоже остаёмся здесь

        logger.debug("Broadcast changes save: %s.", obj)
        # стандартное поведение для обычного «Сохранить»
        return super().response_change(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """При создании рассылки автоматически вносит Бота города админа в форму."""
        if db_field.name == "bot" and not request.user.is_superuser:
            user_city = getattr(request.user, "city", None)
            if user_city:
                bot_qs = db_field.related_model.objects.filter(city=user_city)
                kwargs["queryset"] = bot_qs

                # Устанавливаем initial только при создании
                if bot_qs.count() == 1 and not kwargs.get('instance'):
                    kwargs["initial"] = bot_qs.first()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        user = request.user
        if not user.is_superuser and not change:
            user_city = getattr(user, "city", None)
            if user_city and obj.bot_id is None:
                BotModel = type(obj.bot)  # OrdersBot
                bot_qs = BotModel.objects.filter(city=user_city)
                if bot_qs.count() == 1:
                    obj.bot = bot_qs.first()
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        return has_city_admin_permissions(
            'promos.change_promobroadcast',
            request, obj)

    def progress_display(self, obj: PromoBroadcast):
        total = obj.total_recipients or 0
        processed = getattr(obj, "processed_count", 0) or 0
        delivered = getattr(obj, "delivered_count", 0) or 0

        if total > 0:
            pct = int((processed / total) * 100)
            return format_html(
                "<b>{}</b>/<b>{}</b> ({}%)<br><small>✅ {}</small>",
                processed, total, pct, delivered
            )
        return format_html("<b>{}</b><br><small>✅ {}</small>", processed, delivered)

    progress_display.short_description = "Прогресс"

    def results_short(self, obj: PromoBroadcast):
        data = getattr(obj, "results_json", None) or {}
        if not data:
            return "—"

        # короткая строка для списка
        keys = [
            "ok",
            "bot was blocked",
            "chat not found",
            "user is deactivated",
            "invalid chat",
            "rate limited",
            "temporary error",
            "error",
            "exception",
        ]
        parts = []
        for k in keys:
            if k in data:
                parts.append(f"{k}:{data[k]}")
        return ", ".join(parts) if parts else "—"

    results_short.short_description = "Результаты"

    def results_display(self, obj: PromoBroadcast):
        data = getattr(obj, "results_json", None) or {}
        if not data:
            return "—"
        pretty = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
        return format_html("<pre style='white-space:pre-wrap'>{}</pre>", pretty)

    results_display.short_description = "Результаты рассылки (JSON)"


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    """Настройки админ панели по источникам."""

    def all_clicks(self, obj):
        return obj._all_clicks
    all_clicks.short_description = format_html(
        'Переходы<br>(всего)'
    )

    def unique_clicks(self, obj):
        return obj._unique_clicks
    unique_clicks.short_description = format_html(
        'Переходы<br>(уник.)'
    )

    def custom_new_users(self, obj):
        return obj.new_users
    custom_new_users.short_description = format_html(
        'Новых<br>польз.'
    )

    def last_click(self, obj):
        return obj._last_click
    last_click.short_description = format_html(
        'Последний<br>переход.'
    )

    def orders_sum(self, obj):
        return obj._orders_sum
    orders_sum.short_description = format_html(
        'Сумма<br>заказов'
    )

    list_display = ['name', 'code',
                    'all_clicks', 'unique_clicks', 'custom_new_users',
                    'last_click', 'orders_sum']
    list_display_links = ('name',)
    list_per_page = 20
    fields = ['name', 'code',
              'created', 'city', 'link',
              'bot']
    readonly_fields = ['code', 'created', 'link'] # базовые

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        orders_sum_subq = Subquery(
            Order.objects
                 .filter(campaign=OuterRef('pk'))
                 .values('campaign')
                 .annotate(total=Sum('final_amount_with_shipping'))
                 .values('total')[:1],
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )

        return (
            qs.annotate(
                _all_clicks=Count('open_events'),
                _unique_clicks=Count('open_events__user', distinct=True),
                _orders_sum=Coalesce(
                    orders_sum_subq,
                    Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                _last_click=Max('open_events__created'),
            )
        )

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj:                 # при редактировании существующей кампании
            ro.append('bot')    # делаем bot нередактируемым
        return ro

    def get_fieldsets(self, request, obj=None):
        if obj is None:  # форма создания
            return (
                (None, {
                    "fields": (
                        ("name",),
                        ("city", "bot"),
                    )
                }),
            )

        # форма редактирования
        return (
            (None, {
                "fields": (
                    ("name", "created",),
                    ("city", "bot"),
                    ("code",),
                    ("link",)
                )
            }),
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """При создании источника автоматически вносит город и Бота города в форму."""
        if db_field.name == "bot" and not request.user.is_superuser:
            user_city = getattr(request.user, "city", None)
            if user_city:
                bot_qs = db_field.related_model.objects.filter(city=user_city)
                kwargs["queryset"] = bot_qs

                # Устанавливаем initial только при создании
                if bot_qs.count() == 1 and not kwargs.get('instance'):
                    kwargs["initial"] = bot_qs.first()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        """Автоматически устанавливаем город для обычных админов"""
        if db_field.name == "city" and not request.user.is_superuser:
            user_city = getattr(request.user, "city", None)
            if user_city:
                kwargs["initial"] = user_city
                kwargs["choices"] = [(user_city, user_city)]

        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def has_change_permission(self, request, obj=None):
        return has_city_admin_permissions(
            'promos.change_campaign',
            request, obj)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):

    def banner_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:60px;width:60px;'
                'object-fit:cover;border-radius:6px;" />',
                obj.image.url,
            )
        return '—'
    banner_preview.short_description = 'Баннер'

    def custom_priority(self, obj):
        # берём то, что мы аннотировали в queryset
        return obj.priority
    custom_priority.short_description = format_html('№<br>п/п')

    def custom_title(self, obj):
        # берём то, что мы аннотировали в queryset
        return obj.title
    custom_title.short_description = format_html('НАЗВАНИЕ<br>(внутреннее)')

    def custom_action_type(self, obj):
        # берём то, что мы аннотировали в queryset
        return obj.get_action_type_display()
    custom_action_type.short_description = format_html('ДЕЙСТВИЕ<br>ПРИ КЛИКЕ')

    def copy_button(self, obj):
        return format_html(
            '<a class="button" href="{}/copy/" '
            'title="Создать новый баннер на основе этого.&#10;'
            'Баннер будет сохранён сразу, но неактивным.&#10;'
            'Вы сможете отредактировать его перед публикацией." '
            'style="white-space:nowrap;">📋 Создать копию</a>',
            obj.pk,
        )
    copy_button.short_description = ''

    list_display = (
        'banner_preview', 'custom_title', 'custom_action_type',
        'city', 'custom_priority', 'is_active',
        'copy_button',
    )
    list_filter  = ('is_active', 'city', 'action_type')
    search_fields = ('title',)
    list_per_page = 20
    list_display_links = ('custom_title',)
    readonly_fields = ('banner_preview', 'created', 'updated',
                       'custom_priority', 'custom_title', 'custom_action_type',
                       'previews_block')
    actions = [*active_actions]

    change_form_template = "promos/banner/change_form.html"
    change_list_template = "promos/banner/change_list.html"

    class Media:
        js = ('my_admin/js/promos/banner_action_type.js',
              'my_admin/js/promos/banner_tooltip.js',
              'my_admin/js/promos/banner_modal_svg_preview_lightbox.js',
              'my_admin/js/promos/banner_live_preview.js')
        css = {
            'all': ('my_admin/css/promos/banner_tooltip.css',
                    'my_admin/css/promos/banner_modal_svg_preview_lightbox.css',
                    'my_admin/css/faq/faq.css')
        }

    def previews_block(self, obj):

        def image_thumb(file_field, size_w, size_h):
            """Превью картинки или плашка-заглушка."""
            if file_field:
                return (
                    f'<a href="#" class="lightbox-trigger" data-src="{file_field.url}">'
                    f'<img src="{file_field.url}" style="'
                    f'width:{size_w}px; height:{size_h}px; '
                    f'object-fit:cover; border-radius:10px; cursor:pointer; '
                    f'border:1px solid #333; background:#111;" /></a>'
                )
            return (
                f'<div style="'
                f'width:{size_w}px; height:{size_h}px; '
                f'border-radius:10px; border:1px dashed #555; '
                f'background:#1e1e1e; display:flex; align-items:center; '
                f'justify-content:center; color:#666; font-size:11px; '
                f'text-align:center; line-height:1.4;">'
                f'нет файла<br>= sr-latn</div>'
            )

        def svg_thumb(file_field, size_w, size_h):
            """Превью SVG или плашка-заглушка."""
            if file_field:
                return (
                    f'<a href="#" class="lightbox-trigger" data-src="{file_field.url}">'
                    f'<img src="{file_field.url}" style="'
                    f'width:{size_w}px; height:{size_h}px; '
                    f'object-fit:contain; border-radius:10px; cursor:pointer; '
                    f'border:1px solid #333; background:#111;" /></a>'
                )
            return (
                f'<div style="'
                f'width:{size_w}px; height:{size_h}px; '
                f'border-radius:10px; border:1px dashed #555; '
                f'background:#1e1e1e; display:flex; align-items:center; '
                f'justify-content:center; color:#666; font-size:11px; '
                f'text-align:center; line-height:1.4;">'
                f'нет файла<br>= sr-latn</div>'
            )

        def lang_label(lang):
            return (
                f'<div style="font-size:11px; color:#9aa4af; '
                f'margin-bottom:4px; text-align:center;">{lang}</div>'
            )

        def group(label, default_thumb, ru_thumb, en_thumb):
            """Блок: крупный дефолт + мелкие ru/en справа."""
            return f'''
                <div style="display:flex; flex-direction:column; gap:6px;">
                    <div style="font-size:12px; font-weight:600;
                                color:#ccc; margin-bottom:4px;">{label}</div>
                    <div style="display:flex; gap:10px; align-items:flex-start;
                                flex-wrap:wrap;">
                        <div>
                            {lang_label('sr-latn (дефолт)')}
                            {default_thumb}
                        </div>
                        <div style="display:flex; flex-direction:column; gap:8px;">
                            <div>
                                {lang_label('ru')}
                                {ru_thumb}
                            </div>
                            <div>
                                {lang_label('en')}
                                {en_thumb}
                            </div>
                        </div>
                    </div>
                </div>
            '''

        banner_group = group(
            'Баннер',
            image_thumb(obj.image, 110, 110),
            image_thumb(obj.image_ru, 60, 60),
            image_thumb(obj.image_en, 60, 60),
        )

        modal_group = ''
        if obj.modal_svg or obj.modal_svg_ru or obj.modal_svg_en:
            modal_group = group(
                'Модальное окно',
                svg_thumb(obj.modal_svg, 130, 200),
                svg_thumb(obj.modal_svg_ru, 70, 108),
                svg_thumb(obj.modal_svg_en, 70, 108),
            )

        return format_html(
            '''
            <div style="display:flex; flex-direction:column; gap:6px;">
                <div style="font-size:12px; color:#9aa4af;">
                    Чтобы изменить изображения, используйте раздел «Файлы» ниже
                </div>
                <div style="display:flex; gap:40px; flex-wrap:wrap;
                            align-items:flex-start;">
                    {}
                    {}
                </div>
            </div>
            ''',
            mark_safe(banner_group),
            mark_safe(modal_group),
        )

    previews_block.short_description = 'Превью'

    def get_fieldsets(self, request, obj=None):
        if obj:
            return BANNER_CHANGE_FIELDSETS

        return BANNER_ADD_FIELDSETS

    # ------------------------------------------------------------------ #
    #  Права доступа                                                       #
    # ------------------------------------------------------------------ #

    def get_queryset(self, request):
        """Все видят все баннеры. Редактирование ограничено has_change_permission."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        user_role = getattr(request.user, 'role', None)
        user_city = getattr(request.user, 'city', None)
        if user_role == 'admin' and user_city:
            return qs   # видит все города — для вдохновения и копирования
        return qs.none()

    def get_ordering(self, request):
        return ['city', 'priority']

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True  # доступ к странице списка
        user_city = getattr(request.user, 'city', None)
        return obj.city == user_city

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    # ------------------------------------------------------------------ #
    #  Автоподстановка города                                              #
    # ------------------------------------------------------------------ #

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        """Городскому админу в дропдауне — только его город."""
        if db_field.name == 'city' and not request.user.is_superuser:
            user_city = getattr(request.user, 'city', None)
            if user_city:
                kwargs['initial'] = user_city
                kwargs['choices'] = [(user_city, user_city)]
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    # ------------------------------------------------------------------ #
    #  Кастомный URL — копирование                                         #
    # ------------------------------------------------------------------ #

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                '<int:pk>/copy/',
                self.admin_site.admin_view(self.copy_view),
                name='promos_banner_copy',
            ),
        ]
        return custom + urls

    def copy_view(self, request, pk):
        original = self.get_object(request, pk)
        if not original:
            messages.error(request, 'Баннер не найден.')
            return redirect('..')

        # Определяем город и приоритет для копии
        city = original.city
        if not request.user.is_superuser:
            user_city = getattr(request.user, 'city', None)
            if user_city:
                city = user_city

        max_priority = (
            Banner.objects.filter(city=city)
            .aggregate(Max('priority'))['priority__max'] or 0
        )
        new_priority = max_priority + 1

        # Собираем все поля оригинала (кроме pk, автополей и файлов)
        SKIP_FIELDS = {'id', 'created', 'updated'}
        FILE_FIELDS = ('image', 'image_ru', 'image_en',
                    'modal_svg', 'modal_svg_ru', 'modal_svg_en')

        kwargs = {}
        for field in Banner._meta.concrete_fields:
            if field.name in SKIP_FIELDS:
                continue
            if field.name in FILE_FIELDS:
                continue

            key = field.attname if field.is_relation else field.name
            kwargs[key] = getattr(original, field.attname)

        kwargs['title'] = f'{original.title} (копия)'
        kwargs['is_active'] = False
        kwargs['city'] = city
        kwargs['priority'] = new_priority

        copy = Banner(**kwargs)

        # Копируем файлы в поля ДО save(), чтобы clean() их видел
        storage = Banner._meta.get_field('image').storage

        def read_file(old_name):
            """Читает файл из storage, возвращает ContentFile или None."""
            if not old_name or not storage.exists(old_name):
                return None, None
            dirname, filename = os.path.split(old_name)
            stem, ext = os.path.splitext(filename)
            new_filename = f'{stem}_copy{ext}'
            with storage.open(old_name, 'rb') as f:
                return new_filename, ContentFile(f.read())

        for field_name in FILE_FIELDS:
            old_field = getattr(original, field_name)
            old_name = old_field.name if old_field else None
            new_filename, content = read_file(old_name)
            if content:
                getattr(copy, field_name).save(new_filename, content, save=False)

        copy.save()  # full_clean() внутри — теперь видит файлы

        messages.success(
            request,
            'Баннер скопирован включая картинки. Отредактируйте и активируйте.'
        )
        return redirect(f'../../{copy.pk}/change/')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'dish':
            kwargs['queryset'] = (
                Dish.objects
                .prefetch_related('translations')
                .order_by('article')
            )
        if db_field.name == 'category':
            kwargs['queryset'] = (
                Category.objects
                .prefetch_related('translations')
                .order_by('priority')
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

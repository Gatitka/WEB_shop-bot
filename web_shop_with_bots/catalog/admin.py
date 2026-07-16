import logging
from collections import defaultdict
from django import forms
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.db.models import OuterRef, Subquery, IntegerField, Prefetch
from django.forms.models import BaseInlineFormSet
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from parler.admin import TranslatableAdmin, TranslatableTabularInline
from django.conf import settings

from api.admin_views import (AdminDishPriceXlsDownloadView,
                             AdminDishPriceXlsUploadView)
from catalog.models import (UOM, Category, Dish, DishCategory,
                     RestaurantDishList, CityDishList,
                     DishCityPrice, DishPartnerPrice, DishPriceMatrixProxy)
from catalog.forms import DishAdminForm
from utils.admin_permissions import (
    has_restaurant_admin_permissions,
    has_city_admin_permissions,
    )
from utils.admin_audit_mixin import ValidationLoggingMixin
from utils.utils import make_inactive, active_actions
from utils.format_admin_validation_error import format_admin_validation_error
from tm_bot.services import send_message_admin_changed_settings


logger = logging.getLogger(__name__)


def make_active_dish(modeladmin, request, queryset):
    activated = 0

    for obj in queryset:
        obj.is_active = True

        try:
            obj.full_clean()
            obj.save()
            activated += 1
        except ValidationError as e:
            modeladmin.message_user(
                request,
                format_admin_validation_error(
                    obj, e,
                    extra_labels={"is_active": "Матрица цен"},
                ),
                level=messages.ERROR,
            )

    if activated:
        modeladmin.message_user(
            request,
            f"Активировано: {activated}",
            level=messages.SUCCESS,
        )
make_active_dish.short_description = "Активировать выбранные"


class CategoryPriorityFilter(admin.RelatedOnlyFieldListFilter):
    """Фильтр категорий, отсортированный по Category.priority."""
    def field_choices(self, field, request, model_admin):
        qs = field.remote_field.model._default_manager.order_by('priority')
        return [(obj.pk, str(obj)) for obj in qs]


class DishCategoryInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        # собираем, что пользователь пытается сохранить (без удалённых)
        rows = []
        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue

            category = form.cleaned_data.get("category")
            dish_priority = form.cleaned_data.get("dish_priority")
            if not category or dish_priority in (None, ""):
                continue

            rows.append((form.instance.pk, category.id, int(dish_priority)))

        # 1) проверка дублей внутри текущей формы (не доходя до БД)
        seen = {}
        for pk, cat_id, pr in rows:
            key = (cat_id, pr)
            if key in seen:
                raise ValidationError(
                    f"В одной категории нельзя повторять № п/п. "
                    f"Дубли в форме: category_id={cat_id}, №={pr}."
                )
            seen[key] = pk

        # 2) проверка дублей в БД с красивым сообщением
        for pk, cat_id, pr in rows:
            qs = DishCategory.objects.select_related("dish", "category").filter(
                category_id=cat_id,
                dish_priority=pr,
            )
            if pk:
                qs = qs.exclude(pk=pk)

            conflict = qs.first()
            if conflict:
                dish_name = conflict.dish.safe_translation_getter("short_name", any_language=True) or ""
                # conflict.dish_id у тебя = article (FK to_field='article')
                raise ValidationError(
                    f"В категории «{conflict.category}» уже есть блюдо с № п/п {pr} — "
                    f"{conflict.dish_id} {dish_name}"
                )

    def _post_clean(self):
        super()._post_clean()

        needle = "with this Category и № п/п already exists"

        for form in self.forms:
            # ошибки лежат в form._errors (ErrorDict)
            if not hasattr(form, "_errors") or not form._errors:
                continue

            nfe = form._errors.get(NON_FIELD_ERRORS)  # NON_FIELD_ERRORS == '__all__'
            if not nfe:
                continue

            filtered = [e for e in nfe if needle not in str(e)]
            if len(filtered) != len(nfe):
                if filtered:
                    form._errors[NON_FIELD_ERRORS] = form.error_class(filtered)
                else:
                    # если после фильтра ничего не осталось — удаляем ключ полностью
                    form._errors.pop(NON_FIELD_ERRORS, None)


class DishCategoryInlineAdmin(admin.TabularInline):
    """Вложенная админка DishCategory для добавления категори блюда
    сразу в админке блюда (через объект Dish)."""
    model = DishCategory
    min_num = 1
    validate_min = True  # включает проверку min_num
    extra = 1
    formset = DishCategoryInlineFormSet

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('dish__translations')


class CityRestrictedPriceInlineMixin:
    city_permission = None
    editable_fields = ()
    can_delete = False

    extra = 0
    min_num = 0
    actions = None

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _can_edit_instance(self, request, instance):
        if not instance or not instance.pk:
            return False

        return has_city_admin_permissions(
            self.city_permission,
            request,
            instance,
        )

    def get_formset(self, request, obj=None, **kwargs):
        FormSet = super().get_formset(request, obj, **kwargs)
        inline_admin = self

        class RestrictedFormSet(FormSet):
            def _construct_form(self, i, **kwargs):
                form = super()._construct_form(i, **kwargs)

                if not inline_admin._can_edit_instance(request, form.instance):
                    for field_name in inline_admin.editable_fields:
                        if field_name in form.fields:
                            value = getattr(form.instance, field_name, "")
                            form.fields[field_name].widget = forms.TextInput(
                                attrs={
                                    "readonly": "readonly",
                                    "class": "vTextField readonly-price-field",
                                    "title": "Недоступно для редактирования: "
                                             "нет прав администратора этого города",
                                }
                            )
                            form.fields[field_name].initial = value
                            form.fields[field_name].required = False

                return form

        return RestrictedFormSet


class DishCityPriceInlineAdmin(CityRestrictedPriceInlineMixin,
                               admin.TabularInline):
    """Пермишены читаются из миксина."""
    model = DishCityPrice

    city_permission = "catalog.change_citydishprice"
    editable_fields = ("price", "discount")

    fields = (
        "city",
        "price",
        "discount",
        "final_price",
    )
    readonly_fields = ("city", "final_price")

    verbose_name = "цена сайта"
    verbose_name_plural = "цены сайта"


class DishPartnerPriceInlineAdmin(CityRestrictedPriceInlineMixin,
                                  admin.TabularInline):
    """Пермишены читаются из миксина."""
    model = DishPartnerPrice

    city_permission = "catalog.change_partnerdishprice"
    editable_fields = ("final_price",)

    fields = (
        "city",
        "partner_category",
        "final_price",
    )
    readonly_fields = ("city", "partner_category")

    verbose_name = "цена партнёра"
    verbose_name_plural = "цены партнёров"


@admin.register(DishPriceMatrixProxy)
class DishPriceMatrixAdmin(admin.ModelAdmin):
    """Админка матрицы цен блюда.

    Использует proxy-модель DishPriceMatrixProxy, чтобы редактировать цены блюда
    отдельно от основной карточки блюда.

    Важно:
    - change form показывает только inline-цены;
    - change list отрисован вручную через change_list_proxi.html;
    - list_display почти не влияет на таблицу списка, потому что result_list
      переопределён в шаблоне.
    """

    # ---------------------------------------------------------------------
    # Базовые настройки админки
    # ---------------------------------------------------------------------

    list_display = (
        "price_matrix_title",
    )  # Таблица списка отрисована вручную в change_list_proxi.html

    list_display_links = ("price_matrix_title",)
    list_per_page = 20

    search_fields = (
        "article",
        "translations__short_name",
    )

    list_filter = (
        "is_active",
        "category",
    )

    inlines = (
        DishCityPriceInlineAdmin,
        DishPartnerPriceInlineAdmin,
    )
    actions = None
    change_form_template = "catalog/dish/change_form.html"
    change_list_template = "catalog/dish/change_list_proxi.html"

    class Media:
        css = {
            "all": (
                "my_admin/css/catalogue/dish_tabs.css",
                "my_admin/css/catalogue/price_matrix.css",
            )
        }

    # ---------------------------------------------------------------------
    # Поля формы proxy-модели
    # ---------------------------------------------------------------------

    def get_fields(self, request, obj=None):
        """Скрываем собственные поля Dish: на форме остаются только inline-цены."""
        return []

    def get_fieldsets(self, request, obj=None):
        """Не показываем fieldsets proxy-модели."""
        return []

    def get_readonly_fields(self, request, obj=None):
        """Readonly-поля proxy-модели не нужны, так как основные поля скрыты."""
        return []

    def get_actions(self, request):
        """Actions отключены для всех."""
        return {}

    # ---------------------------------------------------------------------
    # Queryset
    # ---------------------------------------------------------------------

    def get_queryset(self, request):
        """Заранее подгружаем переводы и цены, чтобы список матрицы не делал N+1."""
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "translations",
                Prefetch(
                    "city_prices",
                    queryset=DishCityPrice.objects.order_by("city"),
                ),
                Prefetch(
                    "partner_prices",
                    queryset=DishPartnerPrice.objects.order_by(
                        "city",
                        "partner_category",
                    ),
                ),
            )
            .order_by("article")
        )

    # ---------------------------------------------------------------------
    # Список матрицы цен
    # ---------------------------------------------------------------------

    def changelist_view(self, request, extra_context=None):
        """Добавляет вкладки, кнопки Excel и данные для кастомной таблицы матрицы."""
        extra_context = extra_context or {}
        extra_context.update({
            "admin_tabs": self._get_changelist_tabs(),
            "show_price_xls_buttons": request.user.is_superuser,
        })

        if request.user.is_superuser:
            extra_context.update({
                "xls_download_url": reverse("admin:download_prices_xls"),
                "xls_load_url": reverse("admin:load_new_prices_xls"),
            })

        response = super().changelist_view(request, extra_context=extra_context)

        try:
            cl = response.context_data["cl"]
        except (AttributeError, KeyError):
            return response

        response.context_data["matrix_rows"] = [
            self._matrix_row(obj)
            for obj in cl.result_list
        ]

        return response

    def _get_changelist_tabs(self):
        """Вкладки переключения между общим списком блюд и матрицей цен."""
        return [
            {
                "title": "Общий данные блюд",
                "url": reverse("admin:catalog_dish_changelist"),
                "active": False,
            },
            {
                "title": "Матрица цен",
                "url": reverse("admin:catalog_dishpricematrixproxy_changelist"),
                "active": True,
            },
        ]

    # ---------------------------------------------------------------------
    # Форма редактирования матрицы цен
    # ---------------------------------------------------------------------

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """Добавляет вкладки переключения между карточкой блюда и матрицей цен."""
        extra_context = extra_context or {}
        extra_context["admin_tabs"] = self._get_changeform_tabs(object_id)

        return super().change_view(request, object_id, form_url, extra_context)

    def _get_changeform_tabs(self, object_id):
        """Вкладки внутри карточки конкретного блюда."""
        return [
            {
                "title": "Карточка блюда",
                "url": reverse("admin:catalog_dish_change", args=[object_id]),
                "active": False,
            },
            {
                "title": "Матрица цен",
                "url": reverse(
                    "admin:catalog_dishpricematrixproxy_change",
                    args=[object_id],
                ),
                "active": True,
            },
        ]

    # ---------------------------------------------------------------------
    # Данные для кастомной таблицы списка
    # ---------------------------------------------------------------------

    def _matrix_row(self, obj):
        """Готовит одну строку для таблицы матрицы цен."""
        bg = self._prices_for_city(obj, "Beograd")
        ns = self._prices_for_city(obj, "NoviSad")

        return {
            "pk": obj.pk,
            "is_active": obj.is_active,
            "is_active_icon": self._active_icon_html(obj.is_active),
            "title": str(obj),
            "change_url": reverse(
                "admin:catalog_dishpricematrixproxy_change",
                args=[obj.pk],
            ),
            "bg": bg,
            "ns": {
                "site": self._mark_diff(ns["site"], bg["site"]),
                "p1": self._mark_diff(ns["p1"], bg["p1"]),
                "p2": self._mark_diff(ns["p2"], bg["p2"]),
            },
        }

    def _prices_for_city(self, obj, city):
        site = None
        p1 = None
        p2 = None

        for item in obj.city_prices.all():
            if item.city == city:
                site = item.final_price

        for item in obj.partner_prices.all():
            if item.city == city and item.partner_category == "P1":
                p1 = item.final_price
            elif item.city == city and item.partner_category == "P2":
                p2 = item.final_price

        return {
            "site": {"value": self._fmt_price(site), "raw": site},
            "p1": {"value": self._fmt_price(p1), "raw": p1},
            "p2": {"value": self._fmt_price(p2), "raw": p2},
        }

    def _mark_diff(self, current, base):
        """Помечает цену как отличающуюся от базового города."""
        current["diff"] = current["raw"] != base["raw"]
        return current

    def _fmt_price(self, value):
        """Форматирует цену для компактного отображения в списке."""
        if value in (None, ""):
            return "—"
        return f"{value:.0f}"

    def _active_icon_html(self, is_active):
        """Возвращает стандартную django-иконку boolean-поля."""
        icon = "icon-yes.svg" if is_active else "icon-no.svg"
        alt = "True" if is_active else "False"

        return format_html(
            '<img src="/static/admin/img/{}" alt="{}">',
            icon,
            alt,
        )

    # ---------------------------------------------------------------------
    # Поля стандартного list_display
    # ---------------------------------------------------------------------

    def price_matrix_title(self, obj):
        """Название блюда для стандартного list_display и fallback-отображения."""
        name = obj.safe_translation_getter(
            "short_name",
            language_code="ru",
            any_language=True,
        ) or ""
        return f"{obj.article} {name}".strip()

    price_matrix_title.short_description = "Блюдо"

    # ---------------------------------------------------------------------
    # Доступность в меню админки
    # ---------------------------------------------------------------------

    def has_module_permission(self, request):
        """Скрывает proxy-модель из левого меню админки."""
        return False

    # ---------------------------------------------------------------------
    # Отправка сообщения в админский чат об изменении цены
    # ---------------------------------------------------------------------

    def save_related(self, request, form, formsets, change):
        old_prices = self._get_price_snapshot(form.instance) if change else {}

        super().save_related(request, form, formsets, change)

        new_prices = self._get_price_snapshot(form.instance)
        self._notify_price_changes(request, form.instance, old_prices, new_prices)

    def _get_price_snapshot(self, dish):
        snapshot = {}

        for item in DishCityPrice.objects.filter(dish=dish):
            snapshot[(item.city, "site")] = item.final_price

        for item in DishPartnerPrice.objects.filter(dish=dish):
            snapshot[(item.city, item.partner_category)] = item.final_price

        return snapshot

    def _notify_price_changes(self, request, dish, old_prices, new_prices):
        changed_by_city = defaultdict(list)
        all_keys = set(old_prices) | set(new_prices)

        for city, price_type in sorted(all_keys):
            old_value = old_prices.get((city, price_type))
            new_value = new_prices.get((city, price_type))

            if old_value == new_value:
                continue

            label = {
                "site": "Сайт",
                "P1": "Партнёры P1",
                "P2": "Партнёры P2",
            }.get(price_type, price_type)

            changed_by_city[city].append(
                f"• {label}: {old_value or '—'} → {new_value or '—'}"
            )

        if not changed_by_city:
            return

        admin_email = request.user.email
        dish_name = dish.safe_translation_getter(
            "short_name",
            language_code="ru",
            any_language=True,
        ) or ""

        for city, changes in changed_by_city.items():
            lines = [
                f"💰 Изменение цены: {dish.article} {dish_name}".strip(),
                f"🏙 Город: {city}",
                f"👤 Автор: {admin_email}",
                *changes,
            ]
            send_message_admin_changed_settings("\n".join(lines), city)



@admin.register(Dish)
class DishAdmin(ValidationLoggingMixin, TranslatableAdmin):
    """Настройки админ панели блюд."""
    def custom_vegan_icon(self, obj):
        # краткое название поля в list
        if obj.vegan_icon is False:
            return '-'
        return '+'
    custom_vegan_icon.short_description = format_html('веган<br>икн')

    def custom_spicy_icon(self, obj):
        # краткое название поля в list
        if obj.spicy_icon is False:
            return '-'
        return '+'
    custom_spicy_icon.short_description = format_html('остро<br>икн')

    def custom_priority(self, obj):
        # берём то, что мы аннотировали в queryset
        return getattr(obj, "_cat_dish_priority", "") or ""
    custom_priority.short_description = format_html('№<br>п/п')
    custom_priority.admin_order_field = "_cat_dish_priority"

    # form = DishAdminForm
    readonly_fields = ('id', 'admin_photo', 'created',
                       'custom_priority')
    list_display = ('id', 'article', 'is_active', 'custom_priority',
                    'short_name',
                    'custom_spicy_icon', 'custom_vegan_icon', 'includes_standard_set')   # 'admin_photo')
    list_filter = ('is_active',
                   ('category', CategoryPriorityFilter),
                   'includes_standard_set',
                   'spicy_icon',
                   'vegan_icon')
    list_per_page = 20

    search_fields = ('translations__short_name__icontains',
                     'translations__text__icontains',
                     'article',
                     'id')
    inlines = (
        DishCategoryInlineAdmin,
        # DishCityPriceInlineAdmin,
        # DishPartnerPriceInlineAdmin,
    )
    actions = [make_active_dish, make_inactive]  # спец активация, т.к. делается проверка связанных объектов
    list_select_related = False
    list_display_links = ('article',)
    change_list_template = 'catalog/dish/change_list.html'
    change_form_template = "catalog/dish/change_form.html"
    class Media:
        css = {
            "all": ("my_admin/css/catalogue/dish_tabs.css",)
        }

    fieldsets = (
        ('Основное', {
            'fields': (
                ('article', 'is_active'),
                ('id', 'created'),
                # ('priority'),
                ('spicy_icon', 'vegan_icon', 'includes_standard_set'),
            )
        }),
        ('Тексты для сайта', {
            'fields': (
                ('short_name'),
                ('text'),
            )
        }),
        ('Характеристики', {
            'fields': (
                ('weight_volume', 'weight_volume_uom',),
                ('units_in_set', 'units_in_set_uom'),
                ('utensils')
            )
        }),
        ('Изображение', {
            'fields': ('admin_photo', 'image'),
        })
    )

    # надстройка для увеличения размера текстового поля
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name in ['short_name', 'text',
                             'msngr_short_name', 'msngr_text']:
            kwargs['widget'] = admin.widgets.AdminTextareaWidget(
                attrs={'rows': 3, 'cols': 40}
            )
        return super().formfield_for_dbfield(db_field, **kwargs)

    # def get_queryset(self, request):
    #     return super().get_queryset(request).prefetch_related('translations')

    def get_queryset(self, request):
        qs = super().get_queryset(request).prefetch_related('translations')

        # когда фильтр category__slug в админке выбран, параметр обычно такой:
        # ?category__slug__exact=rolls
        filter_category_id = request.GET.get("category__id__exact")
        if not filter_category_id:
            # если не выбрано — просто пустое поле
            return qs

        pr_sub = DishCategory.objects.filter(
            dish=OuterRef("pk"),
            category__id=filter_category_id
        ).values("dish_priority")[:1]

        return qs.annotate(
            _cat_dish_priority=Subquery(pr_sub, output_field=IntegerField())
        )

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except ValidationError as e:
            self.message_user(request, str(e), level=messages.ERROR)

    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path(
                "download_prices_xls/",
                AdminDishPriceXlsDownloadView.as_view(),
                name="download_prices_xls",
            ),
            path(
                "load_new_prices_xls/",
                AdminDishPriceXlsUploadView.as_view(),
                name="load_new_prices_xls",
            ),
        ]

        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        try:
            extra_context = extra_context or {}
            extra_context["admin_tabs"] = [
                {
                    "title": "Общий список блюд",
                    "url": reverse("admin:catalog_dish_changelist"),
                    "active": True,
                },
                {
                    "title": "Матрица цен",
                    "url": reverse("admin:catalog_dishpricematrixproxy_changelist"),
                    "active": False,
                },
            ]
            extra_context["show_price_xls_buttons"] = request.user.is_superuser

            if request.user.is_superuser:
                extra_context['xls_download_url'] = reverse('admin:download_prices_xls')
                extra_context['xls_load_url'] = reverse('admin:load_new_prices_xls')

            return super(DishAdmin, self).changelist_view(
                request, extra_context=extra_context)
        except Exception as e:
            from django.contrib import messages
            from django.http import HttpResponseRedirect
            import traceback
            traceback.print_exc()
            messages.error(request, f"Ошибка: {type(e).__name__}: {e}")
            return HttpResponseRedirect(request.path)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}

        extra_context["admin_tabs"] = [
            {
                "title": "Карточка блюда",
                "url": reverse("admin:catalog_dish_change", args=[object_id]),
                "active": True,
            },
            {
                "title": "Матрица цен",
                "url": reverse("admin:catalog_dishpricematrixproxy_change", args=[object_id]),
                "active": False,
            },
        ]

        obj = self.get_object(request, object_id)

        if obj:
            errors = obj.get_price_matrix_activation_errors()
            if errors:
                extra_context["price_matrix_warning"] = {
                    "title": "Нужно заполнить матрицу цен",
                    "text": (
                        "Для этого блюда ещё не заполнены цены. "
                        "Пока матрица цен не заполнена, блюдо нельзя активировать и показать на сайте."
                    ),
                    "items": errors,
                    "matrix_url": reverse(
                        "admin:catalog_dishpricematrixproxy_change",
                        args=[obj.pk],
                    ),
                }

        return super().change_view(request, object_id, form_url, extra_context)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        if change:
            return

        dish = form.instance

        for city, _ in settings.CITY_CHOICES:
            DishCityPrice.objects.get_or_create(
                dish=dish,
                city=city,
            )

            for partner_category, _ in settings.PARTNERS_PRICE_CATEGORIES:
                DishPartnerPrice.objects.get_or_create(
                    dish=dish,
                    city=city,
                    partner_category=partner_category,
                )

        price_matrix_url = reverse(
            "admin:catalog_dishpricematrixproxy_change",
            args=[dish.pk],
        )

        self.message_user(
            request,
            format_html(
                """
                <div>
                    <strong>Блюдо создано.</strong><br>
                    Для него создана пустая матрица цен.<br>
                    Не забудьте <a href="{}">внести цены в матрице цен</a>.<br>
                    <strong>Без цен блюдо нельзя активировать и показать на сайте.</strong>
                </div>
                """,
                price_matrix_url,
            ),
            level=messages.WARNING,
        )

@admin.register(Category)
class CategoryAdmin(TranslatableAdmin):
    """Настройки админ панели категорий."""
    list_display = ('pk', 'priority', 'is_active', 'name', 'slug')
    search_fields = ('translations__name__icontains', 'slug')
    list_filter = ('is_active',)
    actions = [*active_actions]
    exclude = ('messenger_name',)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('translations')


@admin.register(UOM)
class UOMAdmin(TranslatableAdmin):

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('translations')


@admin.register(RestaurantDishList)
class RestaurantDishAdmin(admin.ModelAdmin):
    filter_horizontal = ('dish',)

    def save_related(self, request, form, formsets, change):
        old_dishes = set(
            form.instance.dish.values_list('article', flat=True)
        ) if form.instance.pk else set()

        super().save_related(request, form, formsets, change)

        new_dishes = set(form.instance.dish.values_list('article', flat=True))

        added = new_dishes - old_dishes
        removed = old_dishes - new_dishes

        if not added and not removed:
            return

        admin_email = request.user.email
        restaurant = form.instance.restaurant
        city = getattr(restaurant, 'city', None)
        lines = [f"📋 Изменение Блюда/Ресторан: {restaurant}",
                 f"👤 Автор: {admin_email}",]
        if added:
            lines.append(f"✅ Добавлены: {', '.join(sorted(added))}")
        if removed:
            lines.append(f"❌ Удалены: {', '.join(sorted(removed))}")

        if city:
            send_message_admin_changed_settings("\n".join(lines), city)
        else:
            logger.warning("Restaurant %s has no city, skipping notification", restaurant)

    def has_change_permission(self, request, obj=None):
        return has_restaurant_admin_permissions(
            'catalog.change_restdishlist',
            request, obj)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "dish":
            # Подгружаем все блюда с переводами сразу, если это необходимо
            kwargs["queryset"] = Dish.objects.all().prefetch_related('translations')
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(CityDishList)
class CityDishListAdmin(admin.ModelAdmin):
    filter_horizontal = ('dish',)    # Виджет для удобного управления ManyToMany связью

    def has_change_permission(self, request, obj=None):
        return has_city_admin_permissions(
            'catalog.change_citydishlist',
            request, obj)

    def save_related(self, request, form, formsets, change):
        # запоминаем блюда ДО сохранения
        old_dishes = set(
            form.instance.dish.values_list('article', flat=True)
        ) if form.instance.pk else set()

        super().save_related(request, form, formsets, change)

        # блюда ПОСЛЕ сохранения
        new_dishes = set(form.instance.dish.values_list('article', flat=True))

        added = new_dishes - old_dishes
        removed = old_dishes - new_dishes

        if not added and not removed:
            return

        admin_email = request.user.email
        city = form.instance.city
        lines = [f"📋 Изменение Блюда/Город: {city}",
                 f"👤 Автор: {admin_email}",]
        if added:
            lines.append(f"✅ Добавлены: {', '.join(sorted(added))}")
        if removed:
            lines.append(f"❌ Удалены: {', '.join(sorted(removed))}")

        send_message_admin_changed_settings("\n".join(lines), city)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "dish":
            # Подгружаем все блюда с переводами сразу, если это необходимо
            kwargs["queryset"] = Dish.objects.all().prefetch_related('translations')
        return super().formfield_for_manytomany(db_field, request, **kwargs)

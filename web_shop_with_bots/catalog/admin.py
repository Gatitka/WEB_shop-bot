import logging
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.db.models import OuterRef, Subquery, IntegerField
from django.forms.models import BaseInlineFormSet
from django.urls import path, reverse
from django.utils.html import format_html
from parler.admin import TranslatableAdmin, TranslatableTabularInline

from api.admin_views import (AdminDishPriceXlsDownloadView,
                             AdminDishPriceXlsUploadView)
from catalog.models import (UOM, Category, Dish, DishCategory,
                     RestaurantDishList, CityDishList,
                     DishCityPrice, DishPartnerPrice)
from catalog.forms import DishAdminForm
from utils.admin_permissions import (
    has_restaurant_admin_permissions,
    has_city_admin_permissions)
from utils.admin_audit_mixin import ValidationLoggingMixin
from utils.utils import active_actions
from tm_bot.services import send_message_admin_changed_settings


logger = logging.getLogger(__name__)


def make_active(modeladmin, request, queryset):
    """Добавление действия активации выбранных позиций."""
    queryset.update(is_active=1)


def make_deactive(modeladmin, request, queryset):
    """Добавление действия деактивации выбранных позиций."""
    queryset.update(is_active=0)


make_active.short_description = "Отметить позиции активными"
make_deactive.short_description = "Отметить позиции не активными"


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


class DishCityPriceInlineAdmin(admin.TabularInline):
    model = DishCityPrice
    extra = 0
    min_num = 0
    fields = (
        "city",
        "price",
        "discount",
        "final_price",
    )

    verbose_name = "цена сайта"
    verbose_name_plural = "цены сайта"


class DishPartnerPriceInlineAdmin(admin.TabularInline):
    model = DishPartnerPrice
    extra = 0
    min_num = 0
    fields = (
        "city",
        "partner_category",
        "final_price",
    )

    verbose_name = "цена партнёра"
    verbose_name_plural = "цены партнёров"


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
    readonly_fields = ('id', 'final_price', 'admin_photo', 'created',
                       'custom_priority')
    list_display = ('id', 'article', 'is_active', 'custom_priority',
                    'short_name', 'discount', 'final_price',
                    'custom_spicy_icon', 'custom_vegan_icon', 'includes_standard_set')   # 'admin_photo')
    list_filter = ('is_active',
                   ('category', CategoryPriorityFilter),
                   'includes_standard_set',
                   'spicy_icon',
                   'vegan_icon')
    list_per_page = 20

    search_fields = ('translations__short_name__icontains',
                     'translations__text__icontains')
    inlines = (
        DishCategoryInlineAdmin,
        DishCityPriceInlineAdmin,
        DishPartnerPriceInlineAdmin,
    )
    # actions = [make_active, make_deactive]
    actions = [*active_actions]
    list_select_related = False
    list_display_links = ('article',)
    change_list_template = 'catalog/dish/change_list.html'

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
        ('Цена', {
            'fields': (
                ('price', 'discount'),
                ('final_price'),
                ('final_price_p1'),
                ('final_price_p2'),
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

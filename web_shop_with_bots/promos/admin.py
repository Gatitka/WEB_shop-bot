from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin
from parler.admin import (SortedRelatedFieldListFilter, TranslatableAdmin,
                          TranslatableTabularInline)

from utils.utils import activ_actions

from .models import Promocode, PromoNews, PrivatPromocode


# class SummerAdmin(SummernoteModelAdmin):
@admin.register(PromoNews)
class PromoNewsAdmin(TranslatableAdmin):
    """Настройки админ панели промо-новостей."""
    list_display = ['id', 'title', 'is_active', 'city', 'created', 'admin_image_ru']
    readonly_fields = ('admin_image_ru', 'created',
                       'admin_image_en', 'admin_image_sr_latn')
    actions = [*activ_actions]
    search_fields = ('translations__title__icontains',
                     'translations__full_text__icontains')
    list_filter = ('is_active', 'city')

    fieldsets = (
        ('Основное', {
            'fields': (
                ('created', 'is_active'),
                ('city',),
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


# admin.site.register(PromoNews, SummerAdmin)

@admin.register(Promocode)
class PromocodeAdmin(admin.ModelAdmin):
    """Настройки админ панели промо-новостей."""
    list_display = ['id', 'is_active', 'title_rus', 'promocode']
    readonly_fields = ('id', 'created')
    actions = [*activ_actions]
    search_fields = ('promocode', 'title_rus')
    list_filter = ('is_active',)


@admin.register(PrivatPromocode)
class PrivatPromocodeAdmin(admin.ModelAdmin):
    """Настройки админ панели промо-новостей."""
    list_display = ('id', 'promocode', 'base_profile', 'is_active', 'is_used')
    readonly_fields = ('created',)
    actions = [*activ_actions]
    search_fields = ('promocode', 'base_profile')
    list_filter = ('is_active', 'is_used')

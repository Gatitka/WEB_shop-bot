from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin
from parler.admin import (SortedRelatedFieldListFilter, TranslatableAdmin,
                          TranslatableTabularInline)

from utils.utils import activ_actions

from .models import Promocode, PromoNews


# class SummerAdmin(SummernoteModelAdmin):
@admin.register(PromoNews)
class PromoNewsAdmin(TranslatableAdmin):
    """Настройки админ панели промо-новостей."""
    list_display = ['title', 'is_active', 'city', 'created', 'admin_image_ru']
    readonly_fields = ('admin_image_ru', 'created',
                       'admin_image_en', 'admin_image_sr')
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
                ('image_sr', 'admin_image_sr'),
            )
        }),
    )

    # def get_queryset(self, request):
    #     return super().get_queryset(request).prefetch_related('translations')


# admin.site.register(PromoNews, SummerAdmin)

admin.site.register(Promocode, admin.ModelAdmin)

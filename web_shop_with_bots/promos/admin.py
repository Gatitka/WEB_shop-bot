from django.contrib import admin
from parler.admin import (TranslatableAdmin,
                          TranslatableModelForm)
from django_summernote.widgets import SummernoteWidget
from utils.utils import activ_actions

from .models import PrivatPromocode, Promocode, PromoNews


class PromoNewsForm(TranslatableModelForm):
    class Meta:
        model = PromoNews
        fields = '__all__'
        widgets = {
            'content': SummernoteWidget(),
        }


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
    form = PromoNewsForm
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


@admin.register(Promocode)
class PromocodeAdmin(admin.ModelAdmin):
    """Настройки админ панели промо-новостей."""
    list_display = ['id', 'is_active', 'title_rus', 'code']
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

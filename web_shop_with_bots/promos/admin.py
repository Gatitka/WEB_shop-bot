from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin

from utils.utils import activ_actions

from .models import Promocode, PromoNews

# @admin.register(PromoNews)
# class PromoNewsAdmin(admin.ModelAdmin):
#     """Настройки админ панели промо-новостей."""
#     list_display = [field.name for field in PromoNews._meta.get_fields()]   # show all fields
#     actions = [*activ_actions]


class SummerAdmin(SummernoteModelAdmin):
    list_display = ['title_rus', 'is_active', 'city', 'created', 'admin_photo_rus']
    readonly_fields = ('admin_photo_rus', 'admin_photo_en', 'admin_photo_srb', 'created')
    actions = [*activ_actions]
    search_fields = ('title_rus', 'city', 'text_rus')
    list_filter = ('is_active', 'city')
    summernote_fields = '__all__'

    fieldsets = (
        ('Основное', {
            'fields': (
                ('created', 'is_active'),
                ('city',),
            )
        }),
        ('Описание РУС', {
            'fields': (
                ('title_rus'),
                ('full_text_rus'),
                ('admin_photo_rus', 'image_rus'),
            )
        }),
        ('Описание SRB', {
            'fields': (
                ('title_srb'),
                ('full_text_srb'),
                ('admin_photo_srb', 'image_srb'),
            )
        }),
        ('Описание EN', {
            'fields': (
                ('title_en'),
                ('full_text_en'),
                ('admin_photo_en', 'image_en'),
            )
        }),
    )


admin.site.register(PromoNews, SummerAdmin)

admin.site.register(Promocode, admin.ModelAdmin)

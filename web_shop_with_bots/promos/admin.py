from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin
from utils.utils import activ_actions
from .models import PromoNews, Promocode

# @admin.register(PromoNews)
# class PromoNewsAdmin(admin.ModelAdmin):
#     """Настройки админ панели промо-новостей."""
#     list_display = [field.name for field in PromoNews._meta.get_fields()]   # show all fields
#     actions = [*activ_actions]


class SummerAdmin(SummernoteModelAdmin):
    list_display = ['title_rus', 'is_active', 'city', 'created']
    actions = [*activ_actions]
    search_fields = ('title_rus', 'city', 'text_rus')
    list_filter = ('is_active', 'city')
    summernote_fields = '__all__'


admin.site.register(PromoNews, SummerAdmin)

admin.site.register(Promocode, admin.ModelAdmin)

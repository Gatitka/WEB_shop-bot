from catalog.models import Dish, Category, DishCategory
from delivery_contacts.models import Restaurant, Delivery, DeliveryZone
from tm_bot.models import OrdersBot
from promos.models import Banner
from api.utils.core_cache import invalidate_cache_for_model


def make_active(modeladmin, request, queryset):
    queryset.update(is_active=True)
    invalidate_cache_for_model(queryset.model)


make_active.short_description = "Активировать выбранные"


def make_inactive(modeladmin, request, queryset):
    queryset.update(is_active=False)
    invalidate_cache_for_model(queryset.model)


make_inactive.short_description = "Деактивировать выбранные"

active_actions = [make_active, make_inactive]

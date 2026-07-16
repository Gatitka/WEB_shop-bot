"""
Тесты инвалидации cache.

Проверяют:
- очистку cache при изменении моделей;
- очистку cache после admin actions (activate/deactivate);
- корректность invalidate_cache_for_model(...);
- что связанные endpoints инвалидируются вместе
  (например menu + create_order_* conditions).

Покрываются сценарии:
- изменение Dish / Category / DishCategory;
- изменение Restaurant / Delivery / DeliveryZone;
- изменение PromoNews;
- admin actions make_active / make_inactive.

Это integration тесты consistency между DB state и cache layer.
"""

from unittest.mock import Mock

from django.core.cache import cache
from django.test import TestCase, override_settings

from api.utils.core_cache import (
    CONTACTS_DELIVERY_CACHE_KEY,
    DELIVERY_ZONES_CACHE_KEY,
    PROMONEWS_CACHE_KEY,
    BANNERS_CACHE_KEY,
    TAKEAWAY_CONDITIONS_CACHE_KEY,
    DELIVERY_CONDITIONS_CACHE_KEY,
    MENU_CACHE_KEYS,
    invalidate_cache_for_model,
)
from catalog.models import (Dish, Category, DishCategory,
                            DishPartnerPrice, DishCityPrice)
from delivery_contacts.models import Restaurant, Delivery, DeliveryZone
from promos.models import PromoNews
from tm_bot.models import OrdersBot

from utils.utils import make_active, make_inactive


@override_settings(
    CACHE_TIME=180,
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-cache-invalidation",
        }
    },
)
class CacheInvalidationTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _fill_all_cache_keys(self):
        keys = [
            *MENU_CACHE_KEYS,
            CONTACTS_DELIVERY_CACHE_KEY,
            DELIVERY_ZONES_CACHE_KEY,
            PROMONEWS_CACHE_KEY,
            BANNERS_CACHE_KEY,
            TAKEAWAY_CONDITIONS_CACHE_KEY,
            DELIVERY_CONDITIONS_CACHE_KEY,
        ]

        for key in keys:
            cache.set(key, {"cached": True}, 180)

    def _assert_deleted(self, *keys):
        for key in keys:
            self.assertIsNone(cache.get(key), f"Cache key was not deleted: {key}")

    def _assert_exists(self, *keys):
        for key in keys:
            self.assertIsNotNone(cache.get(key), f"Cache key was unexpectedly deleted: {key}")

    def test_dish_invalidates_menu_and_order_conditions(self):
        self._fill_all_cache_keys()

        invalidate_cache_for_model(Dish)

        self._assert_deleted(
            *MENU_CACHE_KEYS,
            TAKEAWAY_CONDITIONS_CACHE_KEY,
            DELIVERY_CONDITIONS_CACHE_KEY,
            BANNERS_CACHE_KEY,
        )

    def test_category_invalidates_menu_and_order_conditions(self):
        self._fill_all_cache_keys()

        invalidate_cache_for_model(Category)

        self._assert_deleted(
            *MENU_CACHE_KEYS,
            TAKEAWAY_CONDITIONS_CACHE_KEY,
            DELIVERY_CONDITIONS_CACHE_KEY,
            BANNERS_CACHE_KEY,
        )

    def test_dishcategory_invalidates_menu_and_order_conditions(self):
        self._fill_all_cache_keys()

        invalidate_cache_for_model(DishCategory)

        self._assert_deleted(
            *MENU_CACHE_KEYS,
            TAKEAWAY_CONDITIONS_CACHE_KEY,
            DELIVERY_CONDITIONS_CACHE_KEY,
            BANNERS_CACHE_KEY,
        )

    def test_restaurant_invalidates_contacts_and_order_conditions(self):
        self._fill_all_cache_keys()

        invalidate_cache_for_model(Restaurant)

        self._assert_deleted(
            CONTACTS_DELIVERY_CACHE_KEY,
            TAKEAWAY_CONDITIONS_CACHE_KEY,
            DELIVERY_CONDITIONS_CACHE_KEY,
        )

    def test_delivery_invalidates_contacts_and_order_conditions(self):
        self._fill_all_cache_keys()

        invalidate_cache_for_model(Delivery)

        self._assert_deleted(
            CONTACTS_DELIVERY_CACHE_KEY,
            TAKEAWAY_CONDITIONS_CACHE_KEY,
            DELIVERY_CONDITIONS_CACHE_KEY,
        )

    def test_ordersbot_invalidates_contacts_and_order_conditions(self):
        self._fill_all_cache_keys()

        invalidate_cache_for_model(OrdersBot)

        self._assert_deleted(
            CONTACTS_DELIVERY_CACHE_KEY,
            TAKEAWAY_CONDITIONS_CACHE_KEY,
            DELIVERY_CONDITIONS_CACHE_KEY,
        )

    def test_delivery_zone_invalidates_delivery_zones(self):
        self._fill_all_cache_keys()

        invalidate_cache_for_model(DeliveryZone)

        self._assert_deleted(DELIVERY_ZONES_CACHE_KEY)

    def test_promonews_invalidates_promonews(self):
        self._fill_all_cache_keys()

        invalidate_cache_for_model(PromoNews)

        self._assert_deleted(PROMONEWS_CACHE_KEY)

    def test_make_inactive_admin_action_invalidates_cache(self):
        self._fill_all_cache_keys()

        queryset = Mock()
        queryset.model = Dish

        make_inactive(modeladmin=None, request=None, queryset=queryset)

        queryset.update.assert_called_once_with(is_active=False)

        self._assert_deleted(
            *MENU_CACHE_KEYS,
            TAKEAWAY_CONDITIONS_CACHE_KEY,
            DELIVERY_CONDITIONS_CACHE_KEY,
        )

    def test_make_active_admin_action_invalidates_cache(self):
        self._fill_all_cache_keys()

        queryset = Mock()
        queryset.model = Dish

        make_active(modeladmin=None, request=None, queryset=queryset)

        queryset.update.assert_called_once_with(is_active=True)

        self._assert_deleted(
            *MENU_CACHE_KEYS,
            TAKEAWAY_CONDITIONS_CACHE_KEY,
            DELIVERY_CONDITIONS_CACHE_KEY,
        )

    def test_dish_city_price_invalidates_menu(self):
        self._fill_all_cache_keys()

        invalidate_cache_for_model(DishCityPrice)

        self._assert_deleted(
            *MENU_CACHE_KEYS,
            TAKEAWAY_CONDITIONS_CACHE_KEY,
            DELIVERY_CONDITIONS_CACHE_KEY,
            BANNERS_CACHE_KEY,
        )

    def test_dish_partner_price_invalidates_menu(self):
        self._fill_all_cache_keys()

        invalidate_cache_for_model(DishPartnerPrice)

        self._assert_deleted(
            *MENU_CACHE_KEYS,
            TAKEAWAY_CONDITIONS_CACHE_KEY,
            DELIVERY_CONDITIONS_CACHE_KEY,
            BANNERS_CACHE_KEY,
        )

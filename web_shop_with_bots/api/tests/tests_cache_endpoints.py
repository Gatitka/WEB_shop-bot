"""
Тесты cache-aware API endpoints.

Проверяют:
- что endpoints корректно отдают данные из cache;
- что используются ожидаемые cache keys;
- что response соответствует закешированным данным;
- что cache layer работает одинаково для:
    - menu / menu2
    - contacts
    - promonews
    - create_order_takeaway
    - create_order_delivery
    - delivery_zones

Это smoke/integration тесты публичного API уровня cache.
"""


from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(CACHE_TIME=180)
class CachedPublicEndpointsTests(TestCase):
    """
    Проверяем кэширование публичных GET endpoint'ов:
    - /api/v1/menu/
    - /api/v1/menu2/
    - /api/v1/promonews/
    - /api/v1/contacts/
    - /api/v1/create_order_takeaway/
    - /api/v1/create_order_delivery/
    """

    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _assert_endpoint_returns_cached_data(self, url, cache_key, cached_data):
        cache.set(cache_key, cached_data, 180)

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, cached_data)

    def test_menu_endpoint_returns_cached_data(self):
        self._assert_endpoint_returns_cached_data(
            url="/api/v1/menu/",
            cache_key="menu_/api/v1/menu/",
            cached_data=[
                {
                    "article": "TEST_DISH",
                    "translations": {
                        "ru": {"short_name": "Тестовое блюдо"}
                    },
                    "final_price": "100.00",
                }
            ],
        )

    def test_menu2_endpoint_returns_cached_data(self):
        self._assert_endpoint_returns_cached_data(
            url="/api/v1/menu2/",
            cache_key="menu2_/api/v1/menu2/",
            cached_data={
                "categories": [
                    {
                        "slug": "rolls",
                        "translations": {
                            "ru": {"name": "Роллы"}
                        },
                        "articles": ["TEST_DISH"],
                        "priority": 1,
                    }
                ],
                "menu_list": [
                    {
                        "article": "TEST_DISH",
                        "translations": {
                            "ru": {"short_name": "Тестовое блюдо"}
                        },
                    }
                ],
            },
        )

    def test_promonews_endpoint_returns_cached_data(self):
        self._assert_endpoint_returns_cached_data(
            url="/api/v1/promonews/",
            cache_key="promonews",
            cached_data=[
                {
                    "id": 1,
                    "city": "Beograd",
                    "translations": {
                        "ru": {"title": "Акция"}
                    },
                }
            ],
        )

    def test_contacts_endpoint_returns_cached_data(self):
        self._assert_endpoint_returns_cached_data(
            url="/api/v1/contacts/",
            cache_key="contacts_delivery",
            cached_data=[
                {
                    "city": "Beograd",
                    "restaurants": [],
                    "delivery": [],
                    "bots": [],
                },
                {
                    "cash_discount": None,
                },
            ],
        )

    def test_create_order_takeaway_endpoint_returns_cached_data(self):
        self._assert_endpoint_returns_cached_data(
            url="/api/v1/create_order_takeaway/",
            cache_key="create_order_takeaway_conditions",
            cached_data=[
                {
                    "id": 1,
                    "city": "Beograd",
                    "type": "takeaway",
                }
            ],
        )

    def test_create_order_delivery_endpoint_returns_cached_data(self):
        self._assert_endpoint_returns_cached_data(
            url="/api/v1/create_order_delivery/",
            cache_key="create_order_delivery_conditions",
            cached_data=[
                {
                    "id": 2,
                    "city": "Beograd",
                    "type": "delivery",
                }
            ],
        )

"""
Тесты cache-aware API endpoints.

Проверяют:
- что endpoint при попадании в кэш (cache HIT) отдаёт данные ИЗ КЭША,
  а не идёт в БД (доказывается через assertNumQueries(0));
- что используется ожидаемый cache key (сверен построчно с views.py/urls.py);
- что response.data совпадает с тем, что реально лежит в кэше.

Это smoke/integration тесты read-пути cache layer для:
    - menu
    - contacts
    - delivery_zones
    - promonews
    - banners
    - create_order_takeaway
    - create_order_delivery

ВАЖНО — известные пробелы, которые эти тесты СОЗНАТЕЛЬНО не закрывают:

1. menu2 (Menu2ViewSet) — есть рабочий @cache_response("menu2_...") во views.py,
   но роут в urls.py закомментирован:
       # menu_router.register(r'menu2', views.Menu2ViewSet, basename='menu2')
   Пока роут не включён — /api/v1/menu2/ отдаёт 404, тестировать нечего.
   См. test_menu2_route_is_currently_disabled ниже — он специально
   зафиксирован как skip с объяснением, чтобы не потерять это из виду.

2. Тесты ниже проверяют только READ (cache HIT) сценарий: мы руками кладём
   данные в cache.set() и проверяем, что view их отдаёт, не трогая БД.
   Они НЕ проверяют:
   - что при cache MISS view реально считает данные и кладёт их в кэш
     (для этого нужны фабрики моделей — вне зоны этого файла);
   - инвалидацию кэша при изменении Dish/цены/ресторана в админке —
     в admin.py есть закомментированный `# invalidate_cache_for_model(...)`
     в make_active(), что похоже на невключённую или недописанную
     инвалидацию. Стоит завести отдельный интеграционный тест на это
     после уточнения, как инвалидация должна работать.
"""

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from unittest.mock import patch


@override_settings(CACHE_TIME=180)
class CachedPublicEndpointsTests(TestCase):
    """
    Проверяем кэширование публичных GET endpoint'ов.

    Все cache_key ниже сверены построчно с декораторами @cache_response
    в views.py, а URL — с urls.py (роутеры menu_router/contacts_router/
    promos_router/order_router).
    """

    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _assert_endpoint_returns_cached_data(self, url, cache_key, cached_data):
        cache.set(cache_key, cached_data, timeout=settings.CACHE_TIME)

        # Audit-логирование пишет запись в БД на КАЖДЫЙ запрос, включая
        # обслуженные из кэша — это ожидаемо и не то, что мы здесь
        # проверяем. Мокаем его, чтобы assertNumQueries(0) доказывал
        # именно "данные не читались из БД", а не путался с логированием.
        with patch("audit.models.AuditLog.objects.create"):
            with self.assertNumQueries(0):
                response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, cached_data)

    # ------------------------------------------------------------------
    # /api/v1/menu/
    # ------------------------------------------------------------------

    def test_menu_endpoint_returns_cached_data(self):
        """
        cache_key: f"menu_{request.get_full_path()}" (MenuViewSet.list,
        через декоратор @cache_response). Форма menu_list соответствует
        NEWDishMenuSerializer.get_price(), где цена — вложенный словарь
        по городам, а не плоское поле final_price.
        """
        self._assert_endpoint_returns_cached_data(
            url="/api/v1/menu/",
            cache_key="menu_/api/v1/menu/",
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
                        "price": {
                            "Beograd": {
                                "price": "100.00",
                                "final_price": "90.00",
                            }
                        },
                    }
                ],
            },
        )

    def test_menu2_route_is_currently_disabled(self):
        """
        Menu2ViewSet и его @cache_response("menu2_...") существуют
        в views.py, но роут закомментирован в urls.py:
            # menu_router.register(r'menu2', views.Menu2ViewSet, basename='menu2')

        Пока это так — /api/v1/menu2/ вернёт 404, а не 200. Тест
        зафиксирован как заведомо неактуальный, чтобы это не потерялось.
        Как только роут включат обратно — раскомментируй проверку ниже
        и удали skipTest.
        """
        self.skipTest(
            "menu2 роут закомментирован в urls.py — "
            "раскомментируй регистрацию во view, затем удали skip"
        )

        # self._assert_endpoint_returns_cached_data(
        #     url="/api/v1/menu2/",
        #     cache_key="menu2_/api/v1/menu2/",
        #     cached_data={...},
        # )

    # ------------------------------------------------------------------
    # /api/v1/contacts/
    # ------------------------------------------------------------------

    def test_contacts_endpoint_returns_cached_data(self):
        """
        cache_key: "contacts_delivery" (ContactsDeliveryViewSet.list).
        Форма ответа: список словарей по городам + последний элемент
        {"cash_discount": ...} — как формирует сам view.
        """
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

    # ------------------------------------------------------------------
    # /api/v1/delivery_zones/
    # ------------------------------------------------------------------

    def test_delivery_zones_endpoint_returns_cached_data(self):
        """
        cache_key: "delivery_zones" (DeliveryZonesViewSet.list).
        Роут: contacts_router.register(r'delivery_zones', ...).
        Ответ — словарь {city: {zone_id: {...}}}.
        """
        self._assert_endpoint_returns_cached_data(
            url="/api/v1/delivery_zones/",
            cache_key="delivery_zones",
            cached_data={
                "Beograd": {
                    "1": {
                        "name": "Центр",
                        "delivery_cost": "250.00",
                        "is_promo": False,
                        "promo_min_order_amount": None,
                    }
                }
            },
        )

    # ------------------------------------------------------------------
    # /api/v1/promonews/
    # ------------------------------------------------------------------

    def test_promonews_endpoint_returns_cached_data(self):
        """cache_key: "promonews" (PromoNewsViewSet.list)."""
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

    # ------------------------------------------------------------------
    # /api/v1/banners/
    # ------------------------------------------------------------------

    def test_banners_endpoint_returns_cached_data(self):
        """
        cache_key: "banners" (BannerViewSet.list).
        Роут: promos_router.register(r'banners', ...).
        Форма ответа — по BannerSerializer.Meta.fields:
        ('id', 'priority', 'image', 'action').
        """
        self._assert_endpoint_returns_cached_data(
            url="/api/v1/banners/",
            cache_key="banners",
            cached_data=[
                {
                    "id": 1,
                    "priority": 1,
                    "image": "https://example.com/banner.jpg",
                    "action": None,
                }
            ],
        )

    # ------------------------------------------------------------------
    # /api/v1/create_order_takeaway/
    # ------------------------------------------------------------------

    def test_create_order_takeaway_endpoint_returns_cached_data(self):
        """
        cache_key: "create_order_takeaway_conditions"
        (TakeawayOrderViewSet.list).
        """
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

    # ------------------------------------------------------------------
    # /api/v1/create_order_delivery/
    # ------------------------------------------------------------------

    def test_create_order_delivery_endpoint_returns_cached_data(self):
        """
        cache_key: "create_order_delivery_conditions"
        (DeliveryOrderViewSet.list).
        """
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

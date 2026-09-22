"""
Тесты фичи "партнёрское кафе" (Beograd, delivery.type == 'restaurant').
аналог самовывоз, но без 10% скидки

Покрывают:
- is_restaurant_partner / is_restaurant_delivery_active
- get_delivery(): подмену takeaway/delivery на restaurant для партнёра,
  fallback при выключенной фиче, невлияние на обычных пользователей
- мгновенную инвалидацию кэша при переключении Delivery.is_active
- validate_delivery_time для delivery.type == 'restaurant' (баг с
  UnboundLocalError при delivery_time=None, он же "как можно скорее")
- полный цикл через реальные /create_order_takeaway/pre_checkout/ и
  /create_order_takeaway/: расчёт суммы, сохранённый Order, откат на
  стандартный флоу при is_active=False, устойчивость к отсутствующим
  параметрам
"""
from datetime import time, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from catalog.models import (
    Category,
    Dish,
    DishCategory,
    DishCityPrice,
    RestaurantDishList,
)
from delivery_contacts.models import Delivery, Restaurant
from delivery_contacts.services import (
    get_delivery,
    is_restaurant_partner,
    is_restaurant_delivery_active,
    RESTAURANT_DELIVERY_ACTIVE_CACHE_PREFIX,
)
from shop.models import Discount, Order
from shop.validators import validate_delivery_time

User = get_user_model()


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-restaurant-partner",
        }
    },
)
class RestaurantPartnerTestCase(TestCase):
    """Общий сетап: партнёр/обычный юзер, delivery-записи для Beograd."""

    def setUp(self):
        cache.clear()

        self.group = Group.objects.create(name="restaurant_partner_beograd")

        self.partner = User.objects.create_user(
            email="partner@test.rs",
            password="12345678aA!",
            first_name="Партнёр",
            last_name="Кафе",
            phone="+381601111111",
            web_language="ru",
            city="Beograd",
        )
        self.partner.groups.add(self.group)

        self.regular_user = User.objects.create_user(
            email="regular@test.rs",
            password="12345678aA!",
            first_name="Обычный",
            last_name="Гость",
            phone="+381602222222",
            web_language="ru",
            city="Beograd",
        )

        self.takeaway_delivery = Delivery.objects.create(
            type="takeaway",
            city="Beograd",
            is_active=True,
            discount="10.00",
            min_time=time(11, 0),
            max_time=time(22, 0),
        )
        self.delivery_delivery = Delivery.objects.create(
            type="delivery",
            city="Beograd",
            is_active=True,
            min_time=time(11, 30),
            max_time=time(22, 0),
        )
        self.restaurant_delivery = Delivery.objects.create(
            type="restaurant",
            city="Beograd",
            is_active=True,
            min_time=time(11, 0),
            max_time=time(22, 0),
        )

    def tearDown(self):
        cache.clear()

    @staticmethod
    def _fake_request(user, city="Beograd"):
        """Функциям нужны только request.data и request.user."""
        return SimpleNamespace(data={"city": city}, user=user)


# ---------------------------------------------------------------------
# is_restaurant_partner / is_restaurant_delivery_active
# ---------------------------------------------------------------------

class IsRestaurantPartnerTests(RestaurantPartnerTestCase):

    def test_partner_user_is_recognized(self):
        self.assertTrue(is_restaurant_partner(self.partner))

    def test_regular_user_is_not_partner(self):
        self.assertFalse(is_restaurant_partner(self.regular_user))

    def test_anonymous_user_is_not_partner(self):
        self.assertFalse(is_restaurant_partner(AnonymousUser()))


class IsRestaurantDeliveryActiveTests(RestaurantPartnerTestCase):

    def test_returns_true_when_active(self):
        self.assertTrue(is_restaurant_delivery_active("Beograd"))

    def test_returns_false_when_no_such_delivery(self):
        self.assertFalse(is_restaurant_delivery_active("NoviSad"))

    def test_result_is_cached(self):
        cache_key = f"{RESTAURANT_DELIVERY_ACTIVE_CACHE_PREFIX}Beograd"
        self.assertIsNone(cache.get(cache_key))

        is_restaurant_delivery_active("Beograd")

        # значение легло в кэш именно как int (0/1), а не bool —
        # это тот самый фикс под redis.DataError
        self.assertEqual(cache.get(cache_key), 1)

    def test_toggling_is_active_invalidates_cache_immediately(self):
        # прогреваем кэш
        self.assertTrue(is_restaurant_delivery_active("Beograd"))

        # выключаем фичу — сохранение Delivery триггерит существующий
        # сигнал post_save -> invalidate_contacts_cache()
        self.restaurant_delivery.is_active = False
        self.restaurant_delivery.save()

        cache_key = f"{RESTAURANT_DELIVERY_ACTIVE_CACHE_PREFIX}Beograd"
        self.assertIsNone(
            cache.get(cache_key),
            "Кэш не сбросился после сохранения Delivery — "
            "проверь, что ключ добавлен в invalidate_contacts_cache().",
        )
        self.assertFalse(is_restaurant_delivery_active("Beograd"))


# ---------------------------------------------------------------------
# get_delivery()
# ---------------------------------------------------------------------

class GetDeliveryRestaurantOverrideTests(RestaurantPartnerTestCase):

    def test_regular_user_takeaway_unaffected(self):
        request = self._fake_request(self.regular_user)
        delivery = get_delivery(request, "takeaway")
        self.assertEqual(delivery, self.takeaway_delivery)

    def test_regular_user_delivery_unaffected(self):
        request = self._fake_request(self.regular_user)
        delivery = get_delivery(request, "delivery")
        self.assertEqual(delivery, self.delivery_delivery)

    def test_partner_takeaway_is_swapped_to_restaurant(self):
        request = self._fake_request(self.partner)
        delivery = get_delivery(request, "takeaway")
        self.assertEqual(delivery, self.restaurant_delivery)

    def test_partner_delivery_is_also_swapped_to_restaurant(self):
        """Партнёр случайно открыл форму 'Доставка' — всё равно должен
        получить restaurant, без ValidationError и без обычной доставки."""
        request = self._fake_request(self.partner)
        delivery = get_delivery(request, "delivery")
        self.assertEqual(delivery, self.restaurant_delivery)

    def test_partner_falls_back_when_restaurant_delivery_disabled(self):
        self.restaurant_delivery.is_active = False
        self.restaurant_delivery.save()

        request = self._fake_request(self.partner)
        delivery = get_delivery(request, "takeaway")
        self.assertEqual(
            delivery, self.takeaway_delivery,
            "При выключенной фиче партнёр должен получать обычный самовывоз "
            "(со скидкой), а не остаться без delivery вовсе.",
        )

    def test_anonymous_user_unaffected(self):
        request = self._fake_request(AnonymousUser())
        delivery = get_delivery(request, "takeaway")
        self.assertEqual(delivery, self.takeaway_delivery)


# ---------------------------------------------------------------------
# validate_delivery_time — фикс UnboundLocalError для type='restaurant'
# ---------------------------------------------------------------------

class ValidateDeliveryTimeRestaurantTypeTests(RestaurantPartnerTestCase):

    def setUp(self):
        super().setUp()
        with mock.patch(
            "delivery_contacts.models.google_validate_address_and_get_coordinates",
            return_value=(44.8125, 20.4612),
        ):
            self.restaurant = Restaurant.objects.create(
                short_name="партнёр",
                address="ул. Тестовая, 1",
                open_time=time(11, 0),
                close_time=time(22, 0),
                phone="+381601234567",
                city="Beograd",
                is_active=True,
                min_acc_time=time(11, 0),
                max_acc_time=time(21, 50),
            )

    def test_asap_order_within_workhours_does_not_raise(self):
        fixed_now = timezone.make_aware(datetime(2026, 9, 22, 15, 0))
        with mock.patch(
            "shop.validators.timezone.localtime", return_value=fixed_now
        ):
            try:
                validate_delivery_time(
                    None, self.restaurant_delivery, self.restaurant
                )
            except UnboundLocalError:
                self.fail(
                    "validate_delivery_time упал с UnboundLocalError для "
                    "delivery.type == 'restaurant' — фикс не применён."
                )

    def test_asap_order_outside_workhours_raises_validation_error(self):
        fixed_now = timezone.make_aware(datetime(2026, 9, 22, 23, 30))
        with mock.patch(
            "shop.validators.timezone.localtime", return_value=fixed_now
        ):
            with self.assertRaises(ValidationError):
                validate_delivery_time(
                    None, self.restaurant_delivery, self.restaurant
                )


# ---------------------------------------------------------------------
# Полный цикл через реальные эндпоинты
# ---------------------------------------------------------------------

class RestaurantPartnerFullCycleAPITests(RestaurantPartnerTestCase):
    """
    Полный цикл через /create_order_takeaway/pre_checkout/ и
    /create_order_takeaway/ — а не прямой вызов функций.
    """

    def setUp(self):
        super().setUp()
        self.client = APIClient()

        # 10% скидка за самовывоз — реальный источник расчёта,
        # НЕ поле Delivery.discount (оно только для витрины).
        Discount.objects.create(
            type=2,
            discount_perc=Decimal("10.00"),
            is_active=True,
            valid_from=timezone.now() - timedelta(days=1),
            valid_to=timezone.now() + timedelta(days=365),
            title_rus="10% скидка за самовывоз",
        )

        with mock.patch(
            "delivery_contacts.models.google_validate_address_and_get_coordinates",
            return_value=(44.8125, 20.4612),
        ):
            self.restaurant = Restaurant.objects.create(
                short_name="центр",
                address="Milovana Milovanovića 4",
                open_time=time(11, 0),
                close_time=time(22, 0),
                phone="+381601111111",
                city="Beograd",
                is_active=True,
                is_default=True,
                min_acc_time=time(11, 0),
                max_acc_time=time(21, 50),
            )

        category = Category.objects.create(slug="rolls", priority=1, is_active=True)
        self.dish = Dish.objects.create(
            article="001",
            is_active=True,
            weight_volume="250",
            units_in_set="8",
        )
        self.dish.set_current_language('ru')
        self.dish.name = 'Ролл тестовый'
        self.dish.short_name = 'Ролл'
        self.dish.save()

        DishCategory.objects.create(dish=self.dish, category=category, dish_priority=1)

        rest_list, _ = RestaurantDishList.objects.get_or_create(restaurant=self.restaurant)
        rest_list.dish.add(self.dish)

        DishCityPrice.objects.create(
            dish=self.dish, city="Beograd", price=Decimal("1000.00")
        )

        self.pre_checkout_url = "/api/v1/create_order_takeaway/pre_checkout/"
        self.create_url = "/api/v1/create_order_takeaway/"

    def _payload(self, **overrides):
        payload = {
            "source": "website",
            "recipient_name": "Тест Тестов",
            "recipient_phone": "+381601234567",
            "city": "Beograd",
            "restaurant": self.restaurant.id,
            "persons_qty": 1,
            "payment_type": "cash",
            "comment": "",
            "delivery_time": None,
            "promocode": None,
            "orderdishes": [{"dish": "001", "quantity": 1}],
        }
        payload.update(overrides)
        return payload

    # ---------------- обычный клиент: стандартный флоу не сломан ----------------

    def test_regular_user_pre_checkout_gets_10_percent_discount(self):
        self.client.force_authenticate(user=self.regular_user)
        resp = self.client.post(self.pre_checkout_url, self._payload(), format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(Decimal(str(resp.data["total_discount"])), Decimal("100.00"))

    def test_regular_user_create_saves_takeaway_order_with_discount(self):
        self.client.force_authenticate(user=self.regular_user)
        resp = self.client.post(self.create_url, self._payload(), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)

        order = Order.objects.get(user=self.regular_user.base_profile)
        self.assertEqual(order.delivery.type, "takeaway")
        self.assertEqual(order.discounted_amount, Decimal("900.00"))

    # ---------------- партнёр: подмена работает end-to-end ----------------

    def test_partner_pre_checkout_no_discount(self):
        self.client.force_authenticate(user=self.partner)
        resp = self.client.post(self.pre_checkout_url, self._payload(), format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(Decimal(str(resp.data["total_discount"])), Decimal("0.00"))

    def test_partner_create_saves_order_as_restaurant_type_no_discount(self):
        self.client.force_authenticate(user=self.partner)
        resp = self.client.post(self.create_url, self._payload(), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)

        order = Order.objects.get(user=self.partner.base_profile)
        self.assertEqual(order.delivery.type, "restaurant")
        self.assertEqual(order.discounted_amount, Decimal("1000.00"))

    # ---------------- is_active=False — фича выключена целиком через API ----------------

    def test_partner_falls_back_to_standard_takeaway_when_feature_disabled(self):
        self.restaurant_delivery.is_active = False
        self.restaurant_delivery.save()

        self.client.force_authenticate(user=self.partner)
        resp = self.client.post(self.create_url, self._payload(), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)

        order = Order.objects.get(user=self.partner.base_profile)
        self.assertEqual(
            order.delivery.type, "takeaway",
            "При выключенной фиче партнёр должен получать обычный самовывоз."
        )
        self.assertEqual(
            order.discounted_amount, Decimal("900.00"),
            "И при этом — обычную 10% скидку, как любой другой клиент."
        )

    # ---------------- отсутствующие параметры не роняют сервер ----------------

    def test_missing_orderdishes_returns_400_not_500(self):
        self.client.force_authenticate(user=self.regular_user)
        payload = self._payload()
        payload.pop("orderdishes")
        resp = self.client.post(self.create_url, payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_missing_city_does_not_crash_get_delivery(self):
        """city отсутствует в запросе — get_delivery() должен подставить
        DEFAULT_CITY и не упасть с 500, каким бы ни было итоговое решение
        сериализатора по остальным полям."""
        self.client.force_authenticate(user=self.partner)
        payload = self._payload()
        payload.pop("city")
        resp = self.client.post(self.pre_checkout_url, payload, format="json")
        self.assertNotEqual(resp.status_code, 500, resp.data)

    def test_asap_delivery_time_end_to_end_for_partner(self):
        """delivery_time не передан вовсе ('как можно скорее') — тот самый
        баг с UnboundLocalError, теперь через полный цикл сериализатора."""
        self.client.force_authenticate(user=self.partner)
        resp = self.client.post(self.create_url, self._payload(), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)

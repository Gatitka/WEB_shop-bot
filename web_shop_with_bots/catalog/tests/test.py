"""
Тесты модели Banner.

Проверяют актуальную бизнес-логику баннеров:
- обязательные поля для каждого action_type;
- валидность внутренних и внешних ссылок;
- обязательный файл для MODAL_SVG;
- отсутствие обязательной цели для NONE;
- автоматическую очистку полей, не относящихся к выбранному action_type.

Тесты соответствуют текущей модели Banner:
DISH, CATEGORY, INTERNAL, EXTERNAL, MODAL_SVG, NONE.
"""


from decimal import Decimal
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from catalog.admin import DishPriceMatrixAdmin
from catalog.models import (
    Dish,
    DishCityPrice,
    DishPartnerPrice,
    DishPriceMatrixProxy,
)


class DishPriceMatrixAdminNotificationTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = DishPriceMatrixAdmin(DishPriceMatrixProxy, self.site)

        self.user = get_user_model().objects.create_user(
            username="admin",
            email="admin@test.com",
            password="pass",
            is_staff=True,
        )

        self.request = RequestFactory().get("/")
        self.request.user = self.user

        self.dish = Dish.objects.create(
            article="001",
            price=Decimal("1000.00"),
            final_price=Decimal("1000.00"),
            final_price_p1=Decimal("1200.00"),
            final_price_p2=Decimal("1300.00"),
        )

    @patch("catalog.admin.send_message_admin_changed_settings")
    def test_notify_price_changes_sends_message_to_city_chat(self, send_mock):
        old_prices = {
            ("Beograd", "site"): Decimal("1000.00"),
            ("Beograd", "P1"): Decimal("1200.00"),
        }

        new_prices = {
            ("Beograd", "site"): Decimal("1100.00"),
            ("Beograd", "P1"): Decimal("1200.00"),
        }

        self.admin._notify_price_changes(
            self.request,
            self.dish,
            old_prices,
            new_prices,
        )

        send_mock.assert_called_once()
        message, city = send_mock.call_args.args

        self.assertEqual(city, "Beograd")
        self.assertIn("Изменение цены", message)
        self.assertIn("001", message)
        self.assertIn("admin@test.com", message)
        self.assertIn("Сайт: 1000.00 → 1100.00", message)

    @patch("catalog.admin.send_message_admin_changed_settings")
    def test_notify_price_changes_does_not_send_if_price_not_changed(self, send_mock):
        old_prices = {
            ("Beograd", "site"): Decimal("1000.00"),
        }

        new_prices = {
            ("Beograd", "site"): Decimal("1000.00"),
        }

        self.admin._notify_price_changes(
            self.request,
            self.dish,
            old_prices,
            new_prices,
        )

        send_mock.assert_not_called()

"""
Тесты API баннеров.

Проверяют актуальную выдачу баннеров в /api/v1/banners/:
- баннер на блюдо показывается только если блюдо активно и доступно
  в городе и ресторане;
- баннер на категорию показывается только если категория активна и в ней
  есть хотя бы одно доступное блюдо для выбранного города/ресторана;
- статичные баннеры и баннеры-ссылки не зависят от доступности меню;
- API возвращает баннеры в ожидаемой структуре и в порядке priority;
- action в ответе сериализуется корректно для текущих action_type.

Тесты соответствуют текущей модели Banner:
DISH, CATEGORY, INTERNAL, EXTERNAL, MODAL_SVG, NONE.
"""

from decimal import Decimal
from io import BytesIO
import tempfile

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from PIL import Image

from catalog.models import (
    Category,
    CityDishList,
    Dish,
    DishCategory,
    RestaurantDishList,
)
from delivery_contacts.models import Restaurant
from promos.models import Banner


TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(
    CACHE_TIME=180,
    MEDIA_ROOT=TEMP_MEDIA_ROOT,
)
class BannersAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/banners/"
        cache.clear()

        self.restaurant = Restaurant.objects.create(
            short_name="центр",
            address="Test address",
            open_time="11:00",
            close_time="22:00",
            phone="+381 61 111 111",
            city="Beograd",
            is_active=True,
            is_default=True,
        )

        self.category = Category.objects.create(
            slug="rolls",
            priority=1,
            is_active=True,
        )

        self.dish = Dish.objects.create(
            article="T001",
            is_active=True,
            weight_volume="250",
            units_in_set="8",
        )

        DishCategory.objects.create(
            dish=self.dish,
            category=self.category,
            dish_priority=1,
        )

        self.city_list = CityDishList.objects.create(city="Beograd")
        self.city_list.dish.add(self.dish)

        self.restaurant_list = RestaurantDishList.objects.create(
            restaurant=self.restaurant
        )
        self.restaurant_list.dish.add(self.dish)

    def tearDown(self):
        cache.clear()

    def _image(self, name="test.jpg"):
        file = BytesIO()
        image = Image.new("RGB", (500, 500), "white")
        image.save(file, "JPEG")
        file.seek(0)

        return SimpleUploadedFile(
            name,
            file.read(),
            content_type="image/jpeg",
        )

    def _modal_file(self, name="modal.svg"):
        return SimpleUploadedFile(
            name,
            b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',
            content_type="image/svg+xml",
        )

    def _banner(self, action_type, **kwargs):
        priority = kwargs.pop("priority", 1)
        image = kwargs.pop("image", self._image())

        return Banner.objects.create(
            title="Test banner",
            city="Beograd",
            priority=priority,
            is_active=True,
            action_type=action_type,
            image=image,
            **kwargs,
        )

    def _response(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("Beograd", response.data)
        return response

    def _city_banners(self):
        return self._response().data["Beograd"]

    def _banner_ids(self):
        return [item["id"] for item in self._city_banners()]

    def _banner_item(self, banner):
        return next(
            item
            for item in self._city_banners()
            if item["id"] == banner.id
        )

    def _assert_banner_shown(self, banner):
        self.assertIn(banner.id, self._banner_ids())

    def _assert_banner_hidden(self, banner):
        self.assertNotIn(banner.id, self._banner_ids())

    def test_dish_banner_is_shown_when_dish_available_for_city_and_restaurant(self):
        banner = self._banner(
            Banner.ActionType.DISH,
            dish=self.dish,
            restaurant=self.restaurant,
        )

        self._assert_banner_shown(banner)

    def test_dish_banner_is_hidden_when_dish_becomes_inactive(self):
        banner = self._banner(
            Banner.ActionType.DISH,
            dish=self.dish,
            restaurant=self.restaurant,
        )

        self._assert_banner_shown(banner)

        self.dish.is_active = False
        self.dish.save(update_fields=["is_active"])

        self._assert_banner_hidden(banner)

    def test_dish_banner_is_hidden_when_dish_removed_from_city_list(self):
        banner = self._banner(
            Banner.ActionType.DISH,
            dish=self.dish,
            restaurant=self.restaurant,
        )

        self._assert_banner_shown(banner)

        self.city_list.dish.remove(self.dish)

        self._assert_banner_hidden(banner)

    def test_dish_banner_is_hidden_when_dish_removed_from_restaurant_list(self):
        banner = self._banner(
            Banner.ActionType.DISH,
            dish=self.dish,
            restaurant=self.restaurant,
        )

        self._assert_banner_shown(banner)

        self.restaurant_list.dish.remove(self.dish)

        self._assert_banner_hidden(banner)

    def test_category_banner_is_shown_when_category_has_available_dish(self):
        banner = self._banner(
            Banner.ActionType.CATEGORY,
            category=self.category,
            restaurant=self.restaurant,
        )

        self._assert_banner_shown(banner)

    def test_category_banner_is_hidden_when_category_becomes_inactive(self):
        banner = self._banner(
            Banner.ActionType.CATEGORY,
            category=self.category,
            restaurant=self.restaurant,
        )

        self._assert_banner_shown(banner)

        self.category.is_active = False
        self.category.save(update_fields=["is_active"])

        self._assert_banner_hidden(banner)

    def test_category_banner_is_hidden_when_only_dish_becomes_inactive(self):
        banner = self._banner(
            Banner.ActionType.CATEGORY,
            category=self.category,
            restaurant=self.restaurant,
        )

        self._assert_banner_shown(banner)

        self.dish.is_active = False
        self.dish.save(update_fields=["is_active"])

        self._assert_banner_hidden(banner)

    def test_category_banner_is_hidden_when_dish_removed_from_city_list(self):
        banner = self._banner(
            Banner.ActionType.CATEGORY,
            category=self.category,
            restaurant=self.restaurant,
        )

        self._assert_banner_shown(banner)

        self.city_list.dish.remove(self.dish)

        self._assert_banner_hidden(banner)

    def test_category_banner_is_hidden_when_dish_removed_from_restaurant_list(self):
        banner = self._banner(
            Banner.ActionType.CATEGORY,
            category=self.category,
            restaurant=self.restaurant,
        )

        self._assert_banner_shown(banner)

        self.restaurant_list.dish.remove(self.dish)

        self._assert_banner_hidden(banner)

    def test_none_banner_is_not_affected_by_menu_availability(self):
        banner = self._banner(Banner.ActionType.NONE)

        self._assert_banner_shown(banner)

        self.city_list.dish.remove(self.dish)
        self.restaurant_list.dish.remove(self.dish)

        self.dish.is_active = False
        self.dish.save(update_fields=["is_active"])

        self._assert_banner_shown(banner)

    def test_external_banner_is_not_affected_by_menu_availability(self):
        banner = self._banner(
            Banner.ActionType.EXTERNAL,
            url="https://example.com",
        )

        self._assert_banner_shown(banner)

        self.city_list.dish.remove(self.dish)
        self.restaurant_list.dish.remove(self.dish)

        self.dish.is_active = False
        self.dish.save(update_fields=["is_active"])

        self._assert_banner_shown(banner)

    def test_internal_banner_is_not_affected_by_menu_availability(self):
        banner = self._banner(
            Banner.ActionType.INTERNAL,
            url="/menu/rolls",
        )

        self._assert_banner_shown(banner)

        self.city_list.dish.remove(self.dish)
        self.restaurant_list.dish.remove(self.dish)

        self.dish.is_active = False
        self.dish.save(update_fields=["is_active"])

        self._assert_banner_shown(banner)

    def test_modal_svg_banner_is_not_affected_by_menu_availability(self):
        banner = self._banner(
            Banner.ActionType.MODAL_SVG,
            modal_svg=self._modal_file(),
        )

        self._assert_banner_shown(banner)

        self.city_list.dish.remove(self.dish)
        self.restaurant_list.dish.remove(self.dish)

        self.dish.is_active = False
        self.dish.save(update_fields=["is_active"])

        self._assert_banner_shown(banner)

    def test_banners_response_has_expected_structure(self):
        banner = self._banner(
            Banner.ActionType.DISH,
            dish=self.dish,
            restaurant=self.restaurant,
        )

        item = self._banner_item(banner)

        self.assertEqual(
            set(item.keys()),
            {"id", "priority", "image", "action"},
        )

        self.assertIsInstance(item["id"], int)
        self.assertIsInstance(item["priority"], int)

        self.assertIsInstance(item["image"], dict)
        self.assertEqual(
            set(item["image"].keys()),
            {"sr-latn", "ru", "en"},
        )

        self.assertIsInstance(item["action"], dict)
        self.assertEqual(item["action"]["type"], "dish")
        self.assertEqual(
            set(item["action"].keys()),
            {"type", "dish_article"},
        )
        self.assertEqual(item["action"]["dish_article"], self.dish.article)

    def test_banners_are_sorted_by_priority(self):
        banner_3 = self._banner(Banner.ActionType.NONE, priority=13)
        banner_1 = self._banner(Banner.ActionType.NONE, priority=11)
        banner_2 = self._banner(Banner.ActionType.NONE, priority=12)

        banners = [
            item
            for item in self._city_banners()
            if item["id"] in {banner_1.id, banner_2.id, banner_3.id}
        ]

        priorities = [item["priority"] for item in banners]

        self.assertEqual(priorities, sorted(priorities))
        self.assertEqual(len(banners), 3)

    def test_dish_banner_action_structure(self):
        banner = self._banner(
            Banner.ActionType.DISH,
            dish=self.dish,
            restaurant=self.restaurant,
        )

        item = self._banner_item(banner)

        self.assertEqual(
            item["action"],
            {
                "type": "dish",
                "dish_article": self.dish.article,
            },
        )

    def test_category_banner_action_structure(self):
        banner = self._banner(
            Banner.ActionType.CATEGORY,
            category=self.category,
            restaurant=self.restaurant,
        )

        item = self._banner_item(banner)

        self.assertEqual(
            item["action"],
            {
                "type": "category",
                "category_slug": self.category.slug,
            },
        )

    def test_external_banner_action_structure(self):
        banner = self._banner(
            Banner.ActionType.EXTERNAL,
            url="https://example.com",
        )

        item = self._banner_item(banner)

        self.assertEqual(
            item["action"],
            {
                "type": "external",
                "url": "https://example.com",
            },
        )

    def test_internal_banner_action_structure(self):
        banner = self._banner(
            Banner.ActionType.INTERNAL,
            url="/menu/rolls",
        )

        item = self._banner_item(banner)

        self.assertEqual(
            item["action"],
            {
                "type": "internal",
                "url": "/menu/rolls",
            },
        )

    def test_none_banner_action_structure(self):
        banner = self._banner(Banner.ActionType.NONE)

        item = self._banner_item(banner)

        self.assertEqual(item["action"], {"type": "none"})

    def test_modal_svg_banner_action_structure(self):
        banner = self._banner(
            Banner.ActionType.MODAL_SVG,
            modal_svg=self._modal_file(),
            modal_svg_ru=self._modal_file("modal_ru.svg"),
            modal_svg_en=self._modal_file("modal_en.svg"),
        )

        item = self._banner_item(banner)

        self.assertEqual(item["action"]["type"], "modal_svg")
        self.assertEqual(
            set(item["action"].keys()),
            {"type", "modal_svg"},
        )
        self.assertIsInstance(item["action"]["modal_svg"], dict)
        self.assertEqual(
            set(item["action"]["modal_svg"].keys()),
            {"sr-latn", "ru", "en"},
        )
        self.assertTrue(item["action"]["modal_svg"]["sr-latn"])
        self.assertTrue(item["action"]["modal_svg"]["ru"])
        self.assertTrue(item["action"]["modal_svg"]["en"])

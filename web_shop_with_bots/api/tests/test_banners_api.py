"""
Тесты API баннеров.

Проверяют:
- баннер на блюдо скрывается, если блюдо/город/ресторан недоступны;
- баннер на категорию скрывается, если в категории нет доступных блюд;
- баннер на promo news скрывается, если новость неактивна;
- статичный баннер не зависит от меню.
"""

from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from catalog.models import Category, CityDishList, Dish, DishCategory, RestaurantDishList
from delivery_contacts.models import Restaurant
from promos.models import Banner, PromoNews
from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile


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
            priority=1,
            is_active=True,
            price=Decimal("1000.00"),
            final_price=Decimal("1000.00"),
            final_price_p1=Decimal("1000.00"),
            final_price_p2=Decimal("1000.00"),
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

    def _banner(self, action_type, **kwargs):
        priority = kwargs.pop("priority", 1)

        return Banner.objects.create(
            title="Test banner",
            city="Beograd",
            priority=priority,
            is_active=True,
            action_type=action_type,
            image=self._image(),
            **kwargs,
        )

    def _banner_ids(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("Beograd", response.data)

        return [item["id"] for item in response.data["Beograd"]]

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

    def test_promo_news_banner_is_hidden_when_promo_news_becomes_inactive(self):
        promo_news = PromoNews.objects.create(
            is_active=True,
            city="Beograd",
            slug="test-promo",
        )

        banner = self._banner(
            Banner.ActionType.PROMO_NEWS,
            promo_news=promo_news,
        )

        self._assert_banner_shown(banner)

        promo_news.is_active = False
        promo_news.save(update_fields=["is_active"])

        self._assert_banner_hidden(banner)

    def test_static_banner_is_not_affected_by_menu_availability(self):
        banner = self._banner(Banner.ActionType.NONE)

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

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        data = response.data

        self.assertIsInstance(data, dict)
        self.assertIn("Beograd", data)

        city_banners = data["Beograd"]

        self.assertIsInstance(city_banners, list)
        self.assertGreaterEqual(len(city_banners), 1)

        item = next(
            x for x in city_banners
            if x["id"] == banner.id
        )

        self.assertEqual(
            set(item.keys()),
            {"id", "priority", "image", "action"}
        )

        self.assertIsInstance(item["id"], int)
        self.assertIsInstance(item["priority"], int)

        self.assertIsInstance(item["image"], dict)

        self.assertEqual(
            set(item["image"].keys()),
            {"sr-latn", "ru", "en"}
        )

        self.assertIsInstance(item["action"], dict)

        self.assertEqual(item["action"]["type"], "dish")

        self.assertEqual(
            set(item["action"].keys()),
            {"type", "dish_article"}
        )

        self.assertEqual(
            item["action"]["dish_article"],
            self.dish.article
        )

    def test_banners_are_sorted_by_priority(self):
        banner_3 = self._banner(
            Banner.ActionType.NONE,
            priority=13,
        )

        banner_1 = self._banner(
            Banner.ActionType.NONE,
            priority=11,
        )

        banner_2 = self._banner(
            Banner.ActionType.NONE,
            priority=12,
        )

        response = self.client.get(self.url)

        banners = [
            item
            for item in response.data["Beograd"]
            if item["id"] in {
                banner_1.id,
                banner_2.id,
                banner_3.id,
            }
        ]

        priorities = [item["priority"] for item in banners]

        self.assertEqual(priorities, sorted(priorities))
        self.assertEqual(len(banners), 3)

    def test_external_banner_action_structure(self):
        banner = self._banner(
            Banner.ActionType.EXTERNAL,
            external_url="https://example.com",
        )

        response = self.client.get(self.url)

        item = next(
            x for x in response.data["Beograd"]
            if x["id"] == banner.id
        )

        self.assertEqual(
            item["action"],
            {
                "type": "external",
                "external_url": "https://example.com",
            }
        )

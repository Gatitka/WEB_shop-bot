from django.core.exceptions import ValidationError
from django.test import TestCase

from promos.models import Banner, PromoNews
from catalog.models import Category, Dish
from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal


class BannerModelValidationTests(TestCase):
    def setUp(self):
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

        self.promo_news = PromoNews.objects.create(
            slug="promo",
            city="Beograd",
            is_active=True,
        )

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

        return Banner(
            title="Test banner",
            city="Beograd",
            priority=priority,
            is_active=True,
            action_type=action_type,
            image=self._image(),
            **kwargs,
        )

    def test_dish_banner_without_dish_is_invalid(self):
        banner = self._banner(Banner.ActionType.DISH)

        with self.assertRaises(ValidationError):
            banner.full_clean()

    def test_category_banner_without_category_is_invalid(self):
        banner = self._banner(Banner.ActionType.CATEGORY)

        with self.assertRaises(ValidationError):
            banner.full_clean()

    def test_promo_news_banner_without_promo_news_is_invalid(self):
        banner = self._banner(Banner.ActionType.PROMO_NEWS)

        with self.assertRaises(ValidationError):
            banner.full_clean()

    def test_external_banner_without_url_is_invalid(self):
        banner = self._banner(Banner.ActionType.EXTERNAL)

        with self.assertRaises(ValidationError):
            banner.full_clean()

    def test_none_banner_without_target_is_valid(self):
        banner = self._banner(Banner.ActionType.NONE)

        banner.full_clean()

    def test_category_banner_clears_unrelated_action_fields(self):
        banner = self._banner(
            Banner.ActionType.CATEGORY,
            category=self.category,
            dish=self.dish,
            promo_news=self.promo_news,
            external_url="https://example.com",
        )

        banner.full_clean()

        self.assertEqual(banner.category, self.category)
        self.assertIsNone(banner.dish)
        self.assertIsNone(banner.promo_news)
        self.assertEqual(banner.external_url, "")

    def test_dish_banner_clears_unrelated_action_fields(self):
        banner = self._banner(
            Banner.ActionType.DISH,
            dish=self.dish,
            category=self.category,
            promo_news=self.promo_news,
            external_url="https://example.com",
        )

        banner.full_clean()

        self.assertEqual(banner.dish, self.dish)
        self.assertIsNone(banner.category)
        self.assertIsNone(banner.promo_news)
        self.assertEqual(banner.external_url, "")

    def test_external_banner_clears_internal_action_fields(self):
        banner = self._banner(
            Banner.ActionType.EXTERNAL,
            external_url="https://example.com",
            dish=self.dish,
            category=self.category,
            promo_news=self.promo_news,
        )

        banner.full_clean()

        self.assertEqual(banner.external_url, "https://example.com")
        self.assertIsNone(banner.dish)
        self.assertIsNone(banner.category)
        self.assertIsNone(banner.promo_news)

    def test_none_banner_clears_all_action_fields(self):
        banner = self._banner(
            Banner.ActionType.NONE,
            dish=self.dish,
            category=self.category,
            promo_news=self.promo_news,
            external_url="https://example.com",
        )

        banner.full_clean()

        self.assertIsNone(banner.dish)
        self.assertIsNone(banner.category)
        self.assertIsNone(banner.promo_news)
        self.assertEqual(banner.external_url, "")

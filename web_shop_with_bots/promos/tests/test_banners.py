from decimal import Decimal
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from catalog.models import Category, Dish
from promos.models import Banner


class BannerModelValidationTests(TestCase):
    def setUp(self):
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

    def _image(self, name="test.jpg", size=(500, 500)):
        file = BytesIO()
        image = Image.new("RGB", size, "white")
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

        return Banner(
            title="Test banner",
            city="Beograd",
            priority=priority,
            is_active=True,
            action_type=action_type,
            image=image,
            **kwargs,
        )

    def test_dish_banner_without_dish_is_invalid(self):
        banner = self._banner(Banner.ActionType.DISH)

        with self.assertRaises(ValidationError) as exc:
            banner.full_clean()

        self.assertIn("dish", exc.exception.message_dict)

    def test_category_banner_without_category_is_invalid(self):
        banner = self._banner(Banner.ActionType.CATEGORY)

        with self.assertRaises(ValidationError) as exc:
            banner.full_clean()

        self.assertIn("category", exc.exception.message_dict)

    def test_internal_banner_without_url_is_invalid(self):
        banner = self._banner(Banner.ActionType.INTERNAL)

        with self.assertRaises(ValidationError) as exc:
            banner.full_clean()

        self.assertIn("url", exc.exception.message_dict)

    def test_external_banner_without_url_is_invalid(self):
        banner = self._banner(Banner.ActionType.EXTERNAL)

        with self.assertRaises(ValidationError) as exc:
            banner.full_clean()

        self.assertIn("url", exc.exception.message_dict)

    def test_modal_svg_banner_without_modal_file_is_invalid(self):
        banner = self._banner(Banner.ActionType.MODAL_SVG)

        with self.assertRaises(ValidationError) as exc:
            banner.full_clean()

        self.assertIn("modal_svg", exc.exception.message_dict)

    def test_none_banner_without_target_is_valid(self):
        banner = self._banner(Banner.ActionType.NONE)

        banner.full_clean()

    def test_dish_banner_with_dish_is_valid(self):
        banner = self._banner(
            Banner.ActionType.DISH,
            dish=self.dish,
        )

        banner.full_clean()

    def test_category_banner_with_category_is_valid(self):
        banner = self._banner(
            Banner.ActionType.CATEGORY,
            category=self.category,
        )

        banner.full_clean()

    def test_internal_banner_with_relative_url_is_valid(self):
        banner = self._banner(
            Banner.ActionType.INTERNAL,
            url="/menu/rolls",
        )

        banner.full_clean()

    def test_internal_banner_with_external_url_is_invalid(self):
        banner = self._banner(
            Banner.ActionType.INTERNAL,
            url="https://example.com/menu/rolls",
        )

        with self.assertRaises(ValidationError) as exc:
            banner.full_clean()

        self.assertIn("url", exc.exception.message_dict)

    def test_external_banner_with_valid_url_is_valid(self):
        banner = self._banner(
            Banner.ActionType.EXTERNAL,
            url="https://example.com",
        )

        banner.full_clean()

    def test_external_banner_with_invalid_url_is_invalid(self):
        banner = self._banner(
            Banner.ActionType.EXTERNAL,
            url="not-a-valid-url",
        )

        with self.assertRaises(ValidationError) as exc:
            banner.full_clean()

        self.assertIn("url", exc.exception.message_dict)

    def test_modal_svg_banner_with_modal_file_is_valid(self):
        banner = self._banner(
            Banner.ActionType.MODAL_SVG,
            modal_svg=self._modal_file(),
        )

        banner.full_clean()

    def test_category_banner_clears_unrelated_action_fields(self):
        banner = self._banner(
            Banner.ActionType.CATEGORY,
            category=self.category,
            dish=self.dish,
            url="https://example.com",
            modal_svg=self._modal_file(),
            modal_svg_ru=self._modal_file("modal_ru.svg"),
            modal_svg_en=self._modal_file("modal_en.svg"),
        )

        banner.full_clean()

        self.assertEqual(banner.category, self.category)
        self.assertIsNone(banner.dish)
        self.assertEqual(banner.url, "")
        self.assertFalse(banner.modal_svg)
        self.assertFalse(banner.modal_svg_ru)
        self.assertFalse(banner.modal_svg_en)

    def test_dish_banner_clears_unrelated_action_fields(self):
        banner = self._banner(
            Banner.ActionType.DISH,
            dish=self.dish,
            category=self.category,
            url="https://example.com",
            modal_svg=self._modal_file(),
            modal_svg_ru=self._modal_file("modal_ru.svg"),
            modal_svg_en=self._modal_file("modal_en.svg"),
        )

        banner.full_clean()

        self.assertEqual(banner.dish, self.dish)
        self.assertIsNone(banner.category)
        self.assertEqual(banner.url, "")
        self.assertFalse(banner.modal_svg)
        self.assertFalse(banner.modal_svg_ru)
        self.assertFalse(banner.modal_svg_en)

    def test_internal_banner_clears_other_action_fields(self):
        banner = self._banner(
            Banner.ActionType.INTERNAL,
            url="/menu/rolls",
            dish=self.dish,
            category=self.category,
            modal_svg=self._modal_file(),
            modal_svg_ru=self._modal_file("modal_ru.svg"),
            modal_svg_en=self._modal_file("modal_en.svg"),
        )

        banner.full_clean()

        self.assertEqual(banner.url, "/menu/rolls")
        self.assertIsNone(banner.dish)
        self.assertIsNone(banner.category)
        self.assertFalse(banner.modal_svg)
        self.assertFalse(banner.modal_svg_ru)
        self.assertFalse(banner.modal_svg_en)

    def test_external_banner_clears_other_action_fields(self):
        banner = self._banner(
            Banner.ActionType.EXTERNAL,
            url="https://example.com",
            dish=self.dish,
            category=self.category,
            modal_svg=self._modal_file(),
            modal_svg_ru=self._modal_file("modal_ru.svg"),
            modal_svg_en=self._modal_file("modal_en.svg"),
        )

        banner.full_clean()

        self.assertEqual(banner.url, "https://example.com")
        self.assertIsNone(banner.dish)
        self.assertIsNone(banner.category)
        self.assertFalse(banner.modal_svg)
        self.assertFalse(banner.modal_svg_ru)
        self.assertFalse(banner.modal_svg_en)

    def test_modal_svg_banner_clears_other_action_fields(self):
        banner = self._banner(
            Banner.ActionType.MODAL_SVG,
            modal_svg=self._modal_file(),
            modal_svg_ru=self._modal_file("modal_ru.svg"),
            modal_svg_en=self._modal_file("modal_en.svg"),
            dish=self.dish,
            category=self.category,
            url="https://example.com",
        )

        banner.full_clean()

        self.assertTrue(banner.modal_svg)
        self.assertTrue(banner.modal_svg_ru)
        self.assertTrue(banner.modal_svg_en)
        self.assertIsNone(banner.dish)
        self.assertIsNone(banner.category)
        self.assertEqual(banner.url, "")

    def test_none_banner_clears_all_action_fields(self):
        banner = self._banner(
            Banner.ActionType.NONE,
            dish=self.dish,
            category=self.category,
            url="https://example.com",
            modal_svg=self._modal_file(),
            modal_svg_ru=self._modal_file("modal_ru.svg"),
            modal_svg_en=self._modal_file("modal_en.svg"),
        )

        banner.full_clean()

        self.assertIsNone(banner.dish)
        self.assertIsNone(banner.category)
        self.assertEqual(banner.url, "")
        self.assertFalse(banner.modal_svg)
        self.assertFalse(banner.modal_svg_ru)
        self.assertFalse(banner.modal_svg_en)

    def test_banner_image_smaller_than_minimum_size_is_invalid(self):
        banner = self._banner(
            Banner.ActionType.NONE,
            image=self._image(size=(300, 300)),
        )

        with self.assertRaises(ValidationError) as exc:
            banner.full_clean()

        self.assertIn("image", exc.exception.message_dict)

    def test_banner_image_with_wrong_ratio_is_invalid(self):
        banner = self._banner(
            Banner.ActionType.NONE,
            image=self._image(size=(800, 400)),
        )

        with self.assertRaises(ValidationError) as exc:
            banner.full_clean()

        self.assertIn("image", exc.exception.message_dict)

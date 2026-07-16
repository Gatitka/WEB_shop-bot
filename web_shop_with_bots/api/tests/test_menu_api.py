"""
Тесты структуры и логики ответа /api/v1/menu/.

Проверяют (сверено с актуальными serializers.py/views.py —
DishMenuSerializer, единственный сериализатор меню, Menu2/NEW-версии
в коде больше нет):
- верхнеуровневую структуру ответа (categories + menu_list);
- набор полей у элемента menu_list — соответствие
  DishMenuSerializer.Meta.fields (включая is_in_shopping_cart);
- структуру price — вложенный словарь по городам с price/final_price
  (значения — Decimal, а не строки: get_price() в serializers.py
  отдаёт "item.price"/"item.final_price" напрямую из модели, минуя
  DRF DecimalField.to_representation);
- что to_representation() вырезает msngr_short_name/msngr_text из
  translations и добавляет dish_priority в каждую вложенную категорию;
- структуру category внутри блюда (CategorySerializer) и в top-level
  categories, включая то, что translations там содержит только "name"
  (description у Category нет, messenger_name явно вырезается);
- фильтрацию: неактивное блюдо / блюдо в неактивной категории не
  попадают в ответ;
- сортировку категорий по priority и блюд внутри категории по
  dish_priority (DishCategory.dish_priority).

ВАЖНО: MenuViewSet.list() кэширует ответ под фиксированным ключом
f"menu_{request.get_full_path()}" — для "/api/v1/menu/" без query это
всегда один и тот же ключ на все тесты этого файла. cache.clear() в
setUp/tearDown обязателен, иначе тесты будут видеть кэш друг друга.
"""

from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Category, Dish, DishCategory, DishCityPrice


class MenuAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/menu/"
        cache.clear()

        self.category = Category.objects.create(
            slug="rolls",
            priority=1,
            is_active=True,
        )
        self.category.set_current_language("ru")
        self.category.name = "Роллы"
        self.category.save()

        self.dish = Dish.objects.create(
            article="T001",
            is_active=True,
            weight_volume="250",
            units_in_set="8",
        )
        self.dish.set_current_language("ru")
        self.dish.short_name = "Тестовый ролл"
        self.dish.text = "Описание тестового ролла"
        self.dish.save()

        DishCategory.objects.create(
            dish=self.dish,
            category=self.category,
            dish_priority=1,
        )

        # discount=10% от price=500.00 -> final_price=450.00 считается
        # моделью в DishCityPrice.save(), явно передавать final_price
        # бессмысленно — модель его пересчитает сама.
        DishCityPrice.objects.create(
            dish=self.dish,
            city="Beograd",
            price=Decimal("500.00"),
            discount=Decimal("10.00"),
        )

    def tearDown(self):
        cache.clear()

    def _get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def _menu_item(self, article):
        data = self._get()
        return next(
            item for item in data["menu_list"] if item["article"] == article
        )

    def _category_item(self, slug):
        data = self._get()
        return next(c for c in data["categories"] if c["slug"] == slug)

    # ------------------------------------------------------------------
    # Верхнеуровневая структура
    # ------------------------------------------------------------------

    def test_response_has_expected_top_level_keys(self):
        data = self._get()
        self.assertEqual(set(data.keys()), {"categories", "menu_list"})

    # ------------------------------------------------------------------
    # Структура top-level "categories"
    # ------------------------------------------------------------------

    def test_category_item_has_expected_keys(self):
        category_item = self._category_item("rolls")
        self.assertEqual(
            set(category_item.keys()),
            {"slug", "translations", "articles", "priority"},
        )
        self.assertEqual(category_item["priority"], 1)
        self.assertEqual(category_item["articles"], ["T001"])

    def test_category_translations_expose_only_name(self):
        """
        views.py вручную собирает category_translations из name/description/
        messenger_name, но у Category нет поля description (getattr вернёт
        None и отсеется фильтром), а messenger_name явно убирается через
        .pop(). В публичном API должно остаться только name.
        """
        category_item = self._category_item("rolls")
        self.assertEqual(
            category_item["translations"]["ru"],
            {"name": "Роллы"},
        )

    # ------------------------------------------------------------------
    # Структура элемента menu_list
    # ------------------------------------------------------------------

    def test_menu_list_item_has_expected_keys(self):
        item = self._menu_item("T001")
        self.assertEqual(
            set(item.keys()),
            {
                "article", "translations", "category", "price",
                "spicy_icon", "vegan_icon", "image",
                "weight_volume", "weight_volume_uom",
                "units_in_set", "units_in_set_uom",
                "is_in_shopping_cart",
                "utensils", "includes_standard_set",
            },
        )

    def test_menu_list_item_is_in_shopping_cart_is_none_for_anonymous(self):
        """
        get_is_in_shopping_cart читает extra_kwargs['cart_items'] из
        serializer.context, а MenuViewSet.list() кладёт в context только
        {'request': request} — extra_kwargs там нет, значит для обычного
        GET (в т.ч. анонимного) значение всегда None.
        """
        item = self._menu_item("T001")
        self.assertIsNone(item["is_in_shopping_cart"])

    def test_menu_list_item_translations_contain_short_name(self):
        item = self._menu_item("T001")
        self.assertEqual(
            item["translations"]["ru"]["short_name"],
            "Тестовый ролл",
        )

    def test_menu_list_item_translations_exclude_messenger_fields(self):
        """
        DishMenuSerializer.to_representation() явно вырезает
        msngr_short_name/msngr_text из translations перед отдачей —
        в публичном /api/v1/menu/ их быть не должно.
        """
        item = self._menu_item("T001")
        translation = item["translations"]["ru"]
        self.assertNotIn("msngr_short_name", translation)
        self.assertNotIn("msngr_text", translation)

    def test_menu_list_item_category_matches_nested_serializer(self):
        """
        DishMenuSerializer.to_representation() добавляет dish_priority
        в каждую вложенную категорию поверх обычных полей CategorySerializer
        (priority, translations, slug) — это порядковый номер блюда именно
        в этой категории (DishCategory.dish_priority), не путать с
        category["priority"] самой категории.
        """
        item = self._menu_item("T001")
        self.assertEqual(len(item["category"]), 1)
        self.assertEqual(item["category"][0]["slug"], "rolls")
        self.assertEqual(
            set(item["category"][0].keys()),
            {"priority", "translations", "slug", "dish_priority"},
        )
        self.assertEqual(item["category"][0]["dish_priority"], 1)

    # ------------------------------------------------------------------
    # Структура и значения price
    # ------------------------------------------------------------------

    def test_menu_list_item_price_structure_and_values(self):
        item = self._menu_item("T001")
        self.assertEqual(
            item["price"],
            {
                "Beograd": {
                    "price": Decimal("500.00"),
                    "final_price": Decimal("450.00"),
                }
            },
        )

    def test_menu_list_item_price_empty_when_no_city_price(self):
        dish_no_price = Dish.objects.create(
            article="T002",
            is_active=True,
            weight_volume="200",
            units_in_set="6",
        )
        dish_no_price.set_current_language("ru")
        dish_no_price.short_name = "Без цены"
        dish_no_price.save()

        DishCategory.objects.create(
            dish=dish_no_price,
            category=self.category,
            dish_priority=2,
        )

        item = self._menu_item("T002")
        self.assertEqual(item["price"], {})

    # ------------------------------------------------------------------
    # Фильтрация
    # ------------------------------------------------------------------

    def test_inactive_dish_excluded_from_menu(self):
        self.dish.is_active = False
        self.dish.save(update_fields=["is_active"])

        data = self._get()
        articles = [item["article"] for item in data["menu_list"]]
        self.assertNotIn("T001", articles)

    def test_dish_in_inactive_category_excluded_from_menu(self):
        self.category.is_active = False
        self.category.save(update_fields=["is_active"])

        data = self._get()
        articles = [item["article"] for item in data["menu_list"]]
        self.assertNotIn("T001", articles)

        slugs = [c["slug"] for c in data["categories"]]
        self.assertNotIn("rolls", slugs)

    # ------------------------------------------------------------------
    # Сортировка
    # ------------------------------------------------------------------

    def test_categories_sorted_by_priority(self):
        second_category = Category.objects.create(
            slug="drinks",
            priority=2,  # выше, чем у rolls (priority=1) — должна идти следующей
            is_active=True,
        )
        second_dish = Dish.objects.create(
            article="T003",
            is_active=True,
            weight_volume="500",
            units_in_set="1",
        )
        DishCategory.objects.create(
            dish=second_dish,
            category=second_category,
            dish_priority=1,
        )

        data = self._get()
        slugs_in_order = [c["slug"] for c in data["categories"]]
        self.assertEqual(slugs_in_order, ["rolls", "drinks"])

    def test_dishes_within_category_sorted_by_dish_priority(self):
        """
        Вставляем блюда НЕ по порядку приоритета (4, затем 2, затем 3),
        чтобы тест реально проверял сортировку по dish_priority, а не
        случайно совпадал с порядком вставки. T001 (dish_priority=1) уже
        создан в setUp.

        dish_priority уникален в пределах категории
        (UniqueConstraint(['category', 'dish_priority']) на DishCategory),
        поэтому все четыре значения — разные.
        """
        dish_priority_4 = Dish.objects.create(
            article="T005",
            is_active=True,
            weight_volume="150",
            units_in_set="2",
        )
        DishCategory.objects.create(
            dish=dish_priority_4,
            category=self.category,
            dish_priority=4,
        )

        dish_priority_2 = Dish.objects.create(
            article="T004",
            is_active=True,
            weight_volume="300",
            units_in_set="4",
        )
        DishCategory.objects.create(
            dish=dish_priority_2,
            category=self.category,
            dish_priority=2,
        )

        dish_priority_3 = Dish.objects.create(
            article="T006",
            is_active=True,
            weight_volume="100",
            units_in_set="1",
        )
        DishCategory.objects.create(
            dish=dish_priority_3,
            category=self.category,
            dish_priority=3,
        )

        category_item = self._category_item("rolls")
        self.assertEqual(
            category_item["articles"],
            ["T001", "T004", "T006", "T005"],
        )

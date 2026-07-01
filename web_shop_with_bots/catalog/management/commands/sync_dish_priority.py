from __future__ import annotations

import re

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.db.utils import IntegrityError

from catalog.models import Dish, DishCategory


class Command(BaseCommand):
    help = "Проверка и перенос Dish.priority -> DishCategory.dish_priority"

    def handle(self, *args, **options):

        # =============================
        # 1. Проверка блюд с 2+ категориями
        # =============================
        multi_qs = (
            Dish.objects
            .annotate(cat_cnt=Count("category", distinct=True))
            .filter(cat_cnt__gt=1)
            .order_by("-cat_cnt", "article")
        )

        multi_count = multi_qs.count()

        self.stdout.write("\n=== Проверка блюд с несколькими категориями ===")

        if multi_count == 0:
            self.stdout.write("✔ Блюд с 2+ категориями нет.")
        else:
            self.stdout.write(f"⚠ Найдено блюд с 2+ категориями: {multi_count}")
            for dish in multi_qs:
                slugs = list(dish.category.values_list("slug", flat=True))
                self.stdout.write(
                    f" - {dish.article}: priority={dish.priority}, categories={slugs}"
                )

        self.stdout.write("")
        answer = input("Продолжить перенос priority? (yes/no): ").strip().lower()

        if answer not in ("y", "yes"):
            self.stdout.write("Операция отменена.")
            return

        # =============================
        # 2. Перенос
        # =============================
        self.stdout.write("\n=== Начинаем перенос ===")

        try:
            with transaction.atomic():

                links = DishCategory.objects.select_related("dish")

                for link in links:
                    if link.dish and link.dish.priority is not None:
                        link.dish_priority = link.dish.priority
                        link.save(update_fields=["dish_priority"])

        except IntegrityError as e:

            self.stdout.write("\n❌ Ошибка уникальности!")
            self.stdout.write(str(e))

            # Попробуем вытащить category_id и dish_priority из текста ошибки
            m = re.search(r"\(category_id,\s*dish_priority\)=\((\d+),\s*(\d+)\)", str(e))

            if m:
                category_id = int(m.group(1))
                wanted_priority = int(m.group(2))

                self.stdout.write(
                    f"\nКонфликт в категории ID={category_id} "
                    f"для priority={wanted_priority}"
                )

                conflicted = (
                    DishCategory.objects
                    .filter(
                        category_id=category_id,
                        dish__priority=wanted_priority
                    )
                    .values_list("dish_id", flat=True)
                )

                self.stdout.write("Артикулы конфликтующих блюд:")
                for art in conflicted:
                    self.stdout.write(f" - {art}")

            self.stdout.write("\nПеренос НЕ выполнен. Транзакция откатилась.")
            return

        self.stdout.write("\n✔ Перенос успешно завершён.")

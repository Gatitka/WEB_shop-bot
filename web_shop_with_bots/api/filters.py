from django_filters import FilterSet, NumberFilter, filters

from catalog.models import Dish


class CharFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class CategoryFilter(FilterSet):
    """
    Кастомный фильтр фильтрует Queryset на основе query_params:
        Фильтры для всех пользователей:
            tags - рецепты с запрошенным тэгом
            authors - рецепты запрошенного автора

        Фильтры для авторизованых пользователей:
            is_favorited - рецепты находящиеся в избранном
                у текущего пользователя
            is_in_shopping_cart - рецепты, находящихся в корзине
                текущего пользователя
    """

    category = CharFilter(field_name='category__slug', lookup_expr='in')

    class Meta:
        model = Dish
        fields = ['category']

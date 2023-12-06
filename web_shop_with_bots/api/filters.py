# from django_filters import FilterSet, NumberFilter, filters
# from rest_framework import filters as f

# from recipe.models import Recipe


# class CharFilter(filters.BaseInFilter, filters.CharFilter):
#     pass


# class RecipeFilter(FilterSet):
#     """
#     Кастомный фильтр фильтрует Queryset на основе query_params:
#         Фильтры для всех пользователей:
#             tags - рецепты с запрошенным тэгом
#             authors - рецепты запрошенного автора

#         Фильтры для авторизованых пользователей:
#             is_favorited - рецепты находящиеся в избранном
#                 у текущего пользователя
#             is_in_shopping_cart - рецепты, находящихся в корзине
#                 текущего пользователя
#     """

#     tags = CharFilter(field_name='tags__slug', lookup_expr='in')
#     is_favorited = NumberFilter(field_name='favorited',    # поле в модели
#                                 method='filter_favorited')
#     is_in_shopping_cart = NumberFilter(field_name='in_shopping_cart',
#                                        method='filter_in_shopping_cart')

#     def filter_favorited(self, queryset, name, value):
#         """
#         Фильтр используется для отображения списка избранных рецептов в разделе
#         "Избранное". Доступен только для авторизованных пользователей.
#         Фильтрует основной QuerySet, описаный в RecipeViewSet.
#         """
#         if self.request.user.is_authenticated and value == 1:
#             return queryset.filter(favorited__favoriter=self.request.user)
#         return queryset

#     def filter_in_shopping_cart(self, queryset, name, value):
#         """
#         Фильтр используется для отображения списка рецептов, находящихся в
#         разделе "Список покупок". Доступен только для авторизованных
#         пользователей. Фильтрует основной QuerySet, описаный в RecipeViewSet.
#         """
#         if self.request.user.is_authenticated and value == 1:
#             return queryset.filter(in_shopping_cart__owner=self.request.user)
#         return queryset

#     class Meta:
#         model = Recipe
#         fields = ['author', 'tags', 'favorited', 'in_shopping_cart']


# class IngredientFilter(f.SearchFilter):
#     """ Фильтр ингредиентов. """
#     search_param = 'name'

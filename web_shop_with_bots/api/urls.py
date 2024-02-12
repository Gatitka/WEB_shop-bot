from django.conf import settings
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (ContactsDeliveryViewSet, DeleteUserViewSet, MenuViewSet,
                    PromoNewsViewSet, ShoppingCartViewSet, UserAddressViewSet,
                    UserOrdersViewSet, ClientAddressesViewSet)

app_name = 'api'

v1_router = DefaultRouter()


v1_router.register(
    r'menu',
    MenuViewSet,
    basename='menu'
)
v1_router.register(
    r'shopping_cart',
    ShoppingCartViewSet,
    basename='shopping_cart'
)
v1_router.register(
    r'contacts',
    ContactsDeliveryViewSet,
    basename='contacts'
)

v1_router.register(
    'me/my_addresses',
    UserAddressViewSet,
    basename='user_addresses'
)
v1_router.register(
    'me/my_orders',
    UserOrdersViewSet,
    basename='user_orders'
)
v1_router.register(
    r'promonews',
    PromoNewsViewSet,
    basename='promonews'
)

v1_router.register(
    'get_client_addresses/<int:user_id>',
    ClientAddressesViewSet,
    basename='client-addresses'
)

# v1_router.register('auth/users/me/delete', DeleteUserViewSet.as_view({'delete': 'destroy'}), basename='users')

# v1_router.register('auth/users', CustomUserViewSet)
# menu
# delivery contacts
# promos (b-day, takeaway discount)
# profile  (register/login/logout, contacts, addresses, orders, promocodes)
# cart
# order (contact -> address -> delivery date/time, choose payment, order success)
# payment


urlpatterns = [
    path('v1/', include(v1_router.urls)),
    path('v1/auth/users/me/delete/', DeleteUserViewSet.as_view(), name='users'),

    # Djoser создаст набор необходимых эндпоинтов.
    # базовые, для управления пользователями в Django:
    path('v1/auth/', include('djoser.urls')),
    # JWT-эндпоинты, для управления JWT-токенами:
    path('v1/auth/', include('djoser.urls.jwt')),
]

if settings.DEBUG:

    import debug_toolbar
    urlpatterns += (path('__debug__/', include(debug_toolbar.urls)),)

#######----------------------------------------------------------########

# v1_router.register('users', MyUserViewSet)

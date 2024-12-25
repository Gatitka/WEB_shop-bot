from django.conf import settings
from django.urls import include, path
from rest_framework.routers import DefaultRouter, SimpleRouter

from .views import (ContactsDeliveryViewSet, DeliveryOrderViewSet,
                    GetGoogleAPIKeyAPIView, MenuViewSet, MyAddressViewSet,
                    MyOrdersViewSet, MyPromocodesViewSet, MyUserViewSet,
                    PromoNewsViewSet, ShoppingCartViewSet,
                    TakeawayOrderViewSet, UserDataAPIView, GetDiscountsAPIView,
                    DeliveryZonesViewSet,
                    calculate_delivery, get_dish_price, save_bot_order)

app_name = 'api'


if settings.ENVIRONMENT == 'development':
    router_type = DefaultRouter()
elif settings.ENVIRONMENT == 'production':
    router_type = SimpleRouter()


# Создание роутеров для разных разделов API
menu_router = router_type
menu_router.register(r'menu', MenuViewSet, basename='menu')

cart_router = router_type
cart_router.register(r'shopping_cart', ShoppingCartViewSet,
                     basename='shopping_cart')

contacts_router = router_type
contacts_router.register(r'contacts', ContactsDeliveryViewSet,
                         basename='contacts')
contacts_router.register(r'delivery_zones', DeliveryZonesViewSet,
                         basename='delivery_zones')

profile_router = router_type
profile_router.register(r'me/my_addresses', MyAddressViewSet,
                        basename='user_addresses')
profile_router.register(r'me/my_orders', MyOrdersViewSet,
                        basename='user_orders')
profile_router.register(r'me/my_promocodes', MyPromocodesViewSet,
                        basename='user_orders')

promos_router = router_type
promos_router.register(r'promonews', PromoNewsViewSet, basename='promonews')

order_router = router_type
order_router.register(r'create_order_takeaway', TakeawayOrderViewSet,
                      basename='create-order-takeaway')
order_router.register(r'create_order_delivery', DeliveryOrderViewSet,
                      basename='create-order-delivery')

users_router = router_type
users_router.register(r'auth/users', MyUserViewSet, basename='users')

# Сборка всех роутеров в один URL-конфиг
urlpatterns = [
    path('v1/', include(menu_router.urls)),
    path('v1/', include(cart_router.urls)),
    path('v1/', include(contacts_router.urls)),
    path('v1/', include(profile_router.urls)),
    path('v1/', include(promos_router.urls)),
    path('v1/', include(order_router.urls)),
    path('v1/', include(users_router.urls)),
    path('v1/get_dish_price/', get_dish_price, name='get_unit_price'),
    path('v1/get_user_data/', UserDataAPIView.as_view(), name='get_user_data'),
    path('v1/get_discounts/', GetDiscountsAPIView.as_view(),
         name='get_discounts'),
    path('v1/get_google_api_key/', GetGoogleAPIKeyAPIView.as_view(),
         name='get_google_api_key'),
    path('v1/calculate_delivery/', calculate_delivery,
         name='calculate_delivery'),
    path('v1/save_bot_order/', save_bot_order, name='save_bot_order'),

    path('v1/auth/', include('djoser.urls.jwt')),
]

if settings.DEBUG:

    import debug_toolbar
    urlpatterns += (path('__debug__/', include(debug_toolbar.urls)),)

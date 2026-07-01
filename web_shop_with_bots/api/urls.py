from django.conf import settings
from django.urls import include, path
from rest_framework.routers import DefaultRouter, SimpleRouter

import api.views as views

app_name = 'api'

if settings.ENVIRONMENT in ['development', 'test_server']:
    router_type = DefaultRouter()   # вывод всех ссылок
elif settings.ENVIRONMENT == 'production':
    router_type = SimpleRouter()    # не выводит ссылки


# Создание роутеров для разных разделов API
menu_router = router_type
menu_router.register(r'menu', views.MenuViewSet, basename='menu')
menu_router.register(r'menu2', views.Menu2ViewSet, basename='menu2')

cart_router = router_type
cart_router.register(r'shopping_cart', views.ShoppingCartViewSet,
                     basename='shopping_cart')

contacts_router = router_type
contacts_router.register(r'contacts', views.ContactsDeliveryViewSet,
                         basename='contacts')
contacts_router.register(r'delivery_zones', views.DeliveryZonesViewSet,
                         basename='delivery_zones')

profile_router = router_type
profile_router.register(r'me/my_addresses', views.MyAddressViewSet,
                        basename='user_addresses')
profile_router.register(r'me/my_orders', views.MyOrdersViewSet,
                        basename='user_orders')
profile_router.register(r'me/my_promocodes', views.MyPromocodesViewSet,
                        basename='user_orders')

promos_router = router_type
promos_router.register(r'promonews', views.PromoNewsViewSet,
                       basename='promonews')
promos_router.register(r'banners', views.BannerViewSet,
                       basename='banners')

order_router = router_type
order_router.register(r'create_order_takeaway', views.TakeawayOrderViewSet,
                      basename='create-order-takeaway')
order_router.register(r'create_order_delivery', views.DeliveryOrderViewSet,
                      basename='create-order-delivery')

users_router = router_type
users_router.register(r'auth/users', views.MyUserViewSet,
                      basename='users')

# Сборка всех роутеров в один URL-конфиг
urlpatterns = [
    path('v1/menu3/', views.fixed_js_response, name='menu3'),
    path('v1/', include(menu_router.urls)),
    path('v1/', include(cart_router.urls)),
    path('v1/', include(contacts_router.urls)),
    path('v1/', include(profile_router.urls)),
    path('v1/', include(promos_router.urls)),
    path('v1/', include(order_router.urls)),
    # для выдачи разных ответов при логине сделан кастомный JWTCreate view
    # path('v1/auth/jwt/create/', views.MyJWTCreateView.as_view(), name='jwt-create'),
    path('v1/', include(users_router.urls)),
    path('v1/get_dish_price/', views.get_dish_price, name='get_unit_price'),
    path('v1/get_user_data/', views.UserDataAPIView.as_view(), name='get_user_data'),
    path('v1/get_discounts/', views.GetDiscountsAPIView.as_view(),
         name='get_discounts'),
    path('v1/get_google_api_key/', views.GetGoogleAPIKeyAPIView.as_view(),
         name='get_google_api_key'),
    path('v1/calculate_delivery/', views.calculate_delivery,
         name='calculate_delivery'),
    path('v1/save_bot_order/', views.save_bot_order, name='save_bot_order'),

    path('v1/auth/', include('djoser.urls.jwt')),

    path('v1/tmauth/', views.TelegramAuthView.as_view(),
         name='tmauth'),

    path('v1/telegram/subscription/', views.SubscriptionAPIView.as_view(),
         name="telegram_subscription"),
]

if settings.DEBUG:

    import debug_toolbar
    urlpatterns += (path('__debug__/', include(debug_toolbar.urls)),)

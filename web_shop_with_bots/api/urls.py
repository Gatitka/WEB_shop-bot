from django.conf import settings
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from django.urls import re_path
from djoser import views

from .views import (
                    ContactsDeliveryViewSet,
                    # DeleteUserViewSet,
                    MenuViewSet,
                    PromoNewsViewSet,
                    ShoppingCartViewSet,
                    MyAddressViewSet,
                    MyOrdersViewSet,
                    MyPromocodesViewSet,
                    ClientAddressesViewSet,
                    get_unit_price,
                    TakeawayOrderViewSet,
                    DeliveryOrderViewSet,
                    MyUserViewSet)

app_name = 'api'

# Создание роутеров для разных разделов API
menu_router = DefaultRouter()
menu_router.register(r'menu', MenuViewSet, basename='menu')

cart_router = DefaultRouter()
cart_router.register(r'shopping_cart', ShoppingCartViewSet, basename='shopping_cart')

contacts_router = DefaultRouter()
contacts_router.register(r'contacts', ContactsDeliveryViewSet, basename='contacts')

profile_router = DefaultRouter()
profile_router.register(r'me/my_addresses', MyAddressViewSet, basename='user_addresses')
profile_router.register(r'me/my_orders', MyOrdersViewSet, basename='user_orders')
profile_router.register(r'me/my_promocodes', MyPromocodesViewSet, basename='user_orders')

promos_router = DefaultRouter()
promos_router.register(r'promonews', PromoNewsViewSet, basename='promonews')

order_router = DefaultRouter()
order_router.register(r'create_order_takeaway', TakeawayOrderViewSet, basename='create-order-takeaway')
order_router.register(r'create_order_delivery', DeliveryOrderViewSet, basename='create-order-delivery')

users_router = DefaultRouter()
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
    path('v1/get_unit_price/', get_unit_price, name='get_unit_price'),
    path('v1/auth/', include('djoser.urls.jwt')),
    path('v1/token/login/', views.TokenCreateView.as_view(), name='login'),
    path('v1/token/logout/', views.TokenDestroyView.as_view(), name='logout'),
]

if settings.DEBUG:

    import debug_toolbar
    urlpatterns += (path('__debug__/', include(debug_toolbar.urls)),)

#######----------------------------------------------------------########

# v1_router.register('users', MyUserViewSet)

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import MenuViewSet, MyUserViewSet, UserActivationView, ShopViewSet, contacts_delivery

app_name = 'api'

v1_router = DefaultRouter()

v1_router.register('users', MyUserViewSet)
v1_router.register(
    r'menu',
    MenuViewSet,
    basename='menu'
)
# v1_router.register(
#     r'contacts',
#     ShopViewSet,
#     basename='contacts'
# )
# v1_router.register(
#     'contacts',
#     contacts_delivery,
#     'contacts_delivery'
# )


# menu
# delivery contacts
# promos (b-day, takeaway discount)
# profile  (register/login/logout, contacts, addresses, orders, promocodes)
# cart
# order (contact -> address -> delivery date/time, choose payment, order success)
# payment


urlpatterns = [
    path('v1/', include(v1_router.urls)),
    path('v1/contacts/', contacts_delivery, name='contacts_delivery'),
    # Djoser создаст набор необходимых эндпоинтов.
    path('v1/auth/users/activation/<str:uid>/<str:token>/', UserActivationView.as_view()),
    # базовые, для управления пользователями в Django:
    path('v1/auth/', include('djoser.urls')),
    # JWT-эндпоинты, для управления JWT-токенами:
    path('v1/auth/', include('djoser.urls.jwt'))
]

import os
import django

# Настройка Django окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_shop_with_bots.settings')  # Замените 'your_project' на имя вашего проекта
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, ContentType
from catalog.models import CityDishList, RestaurantDishList
from delivery_contacts.models import Restaurant, Delivery, DeliveryZone, Courier
from tm_bot.models import AdminChatTM, OrdersBot

User = get_user_model()


def create_citydish_permissions():
    content_type = ContentType.objects.get_for_model(CityDishList)
    citydishelists = CityDishList.objects.all()
    for citydish in citydishelists:
        change_permission, _ = Permission.objects.get_or_create(
            codename=f'change_citydishlist_{citydish.city}',
            name=f'Can change CityDishList {citydish.city}',
            content_type=content_type
        )
    print("Successfully created citydishlist permissions")


def create_restaurantdish_permissions():
    content_type = ContentType.objects.get_for_model(RestaurantDishList)
    restaurantdishelists = RestaurantDishList.objects.all()
    for restdish in restaurantdishelists:
        change_permission, _ = Permission.objects.get_or_create(
            codename=f'change_restdishlist_{restdish.restaurant_id}',
            name=f'Can change RestaurantDishList {restdish.restaurant_id}',
            content_type=content_type
        )
    print("Successfully created restdishlist permissions")


def create_restaurant_permissions():
    content_type = ContentType.objects.get_for_model(Restaurant)
    restaurants = Restaurant.objects.all()
    for rest in restaurants:
        # Создаем разрешение на изменение
        change_permission, _ = Permission.objects.get_or_create(
            codename=f'change_restaurant_{rest.pk}',
            name=f'Can change Restaurant {rest.pk}',
            content_type=content_type
        )
        change_rest_ord_permission, _ = Permission.objects.get_or_create(
            codename=f'change_orders_rest_{rest.pk}',
            name=f'Can change Restaurant {rest.pk}',
            content_type=content_type
        )
    print("Successfully created restaurant permissions")


def create_delivery_permissions():
    content_type = ContentType.objects.get_for_model(Delivery)
    deliveries = Delivery.objects.all()
    for delivery in deliveries:
        # Создаем разрешение на изменение
        change_permission, _ = Permission.objects.get_or_create(
            codename=f'change_deliveries_{delivery.city}',
            name=f'Can change Deliveries {delivery.city}',
            content_type=content_type
        )
    print("Successfully created delivery permissions")


def create_delivery_zones_permissions():
    content_type = ContentType.objects.get_for_model(DeliveryZone)
    deliverieszones = DeliveryZone.objects.all()
    for deliveryz in deliverieszones:
        # Создаем разрешение на изменение
        change_permission, _ = Permission.objects.get_or_create(
            codename=f'change_delivery_zones_{deliveryz.city}',
            name=f'Can change DeliveryZones {deliveryz.city}',
            content_type=content_type
        )
    print("Successfully created delivery zones permissions")


def create_couriers_permissions():
    content_type = ContentType.objects.get_for_model(Courier)
    couriers = Courier.objects.all()
    for courier in couriers:
        # Создаем разрешение на изменение
        change_permission, _ = Permission.objects.get_or_create(
            codename=f'change_couriers_{courier.city}',
            name=f'Can change Couriers {courier.city}',
            content_type=content_type
        )
    print("Successfully created couriers permissions")


def create_adminchat_permissions():
    content_type = ContentType.objects.get_for_model(AdminChatTM)
    acs = AdminChatTM.objects.all()
    for ac in acs:
        # Создаем разрешение на изменение
        change_permission, _ = Permission.objects.get_or_create(
            codename=f'change_adminchat_{ac.restaurant_id}',
            name=f'Can change AdminChat {ac.restaurant_id}',
            content_type=content_type
        )
    print("Successfully created adminchats permissions")


def create_orderbot_permissions():
    content_type = ContentType.objects.get_for_model(OrdersBot)
    orderbots = OrdersBot.objects.all()
    for ob in orderbots:
        # Создаем разрешение на изменение
        change_permission, _ = Permission.objects.get_or_create(
            codename=f'change_ordersbot_{ob.city}',
            name=f'Can change OrdersBot {ob.city}',
            content_type=content_type
        )
    print("Successfully created orderbots permissions")

if __name__ == '__main__':
    create_citydish_permissions()
    create_restaurantdish_permissions()
    create_restaurant_permissions()
    create_delivery_permissions()
    create_delivery_zones_permissions()
    create_couriers_permissions()
    create_adminchat_permissions()
    create_orderbot_permissions()
    print("Successfully created permissions")

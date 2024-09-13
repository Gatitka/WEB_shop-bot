

def has_restaurant_orders_admin_permissions(request, obj=None):
    if obj is None:
        view = request.GET.get('view', None)
        e = request.GET.get('e', None)

        if view == 'all_orders' or e == '1':
            return False
        else:
            return True
    else:
        # Разрешаем изменение заказа только если есть соответствующие права
        restaurant_id = obj.restaurant.id
        change_perm = request.user.has_perm(
            f'delivery_contacts.can_change_orders_rest_{restaurant_id}')
        return change_perm


def has_city_orders_admin_permissions(request, obj=None):
    if obj is None:
        return False

    else:
        # Разрешаем изменение заказа только если есть соответствующие права
        city = obj.city
        restaurant = request.user.restaurant
        if city == restaurant.city:
            change_perm = request.user.has_perm(
                f'delivery_contacts.can_change_orders_rest_{restaurant.id}')
            return change_perm
        return False



def has_restaurant_admin_permissions(permission, request, obj=None,):
    if request.user.is_superuser:
        return True

    if obj is None:
        view = request.GET.get('view', None)
        e = request.GET.get('e', None)

        if view == 'all_orders' or e == '1':
            return False
        else:
            return True
    else:
        # Разрешаем изменение заказа только если есть соответствующие права
        if obj.__class__.__name__ in ['Restaurant']:
            restaurant_id = obj.id

        else:
            restaurant_id = obj.restaurant_id
        change_perm = request.user.has_perm(
            f'{permission}_{restaurant_id}')
        return change_perm


def has_city_admin_permissions(permission, request, obj=None):
    if request.user.is_superuser:
        return True

    if obj is None:
        return False

    else:
        # Разрешаем изменение заказа только если есть соответствующие права
        change_perm = request.user.has_perm(
            f'{permission}_{obj.city}')
        return change_perm

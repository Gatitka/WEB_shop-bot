from django.conf import settings
from delivery_contacts.models import Delivery


def get_delivery(request, type):
    city = request.data.get('city', settings.DEFAULT_CITY)

    delivery = Delivery.objects.filter(
        city=city,
        type='delivery',
        is_active=True
    ).first()

    return delivery

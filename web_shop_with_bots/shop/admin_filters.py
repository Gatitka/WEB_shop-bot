from django.contrib import admin
from django.conf import settings
from delivery_contacts.models import Courier
from django.utils import timezone
from datetime import timedelta


class DeliveryTypeFilter(admin.SimpleListFilter):
    title = 'Тип доставки'
    parameter_name = 'delivery_type'

    def lookups(self, request, model_admin):
        return settings.DELIVERY_CHOICES

    def queryset(self, request, queryset):
        non_partner_queryset = queryset.exclude(source__in=settings.PARTNERS_LIST)

        if self.value():
            # Then apply the delivery type filter on non-partner orders
            return non_partner_queryset.filter(delivery__type=self.value())
        return queryset


class InvoiceFilter(admin.SimpleListFilter):
    title = 'Наличие чека'
    parameter_name = 'invoice'

    def lookups(self, request, model_admin):
        return ((True, "есть чек"), (False, "без чека"))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(invoice=self.value())
        return queryset


class CourierFilter(admin.SimpleListFilter):
    title = 'Курьер'
    parameter_name = 'courier'

    def lookups(self, request, model_admin):
        couriers = Courier.objects.all()
        choices = [(c.id, str(c)) for c in couriers]
        # Добавляем "нет" вместо "-" для случая None
        choices.append((None, '-------'))
        return choices

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        elif self.value() == 'None':  # Для случая "нет курьера"
            return queryset.filter(courier__isnull=True)
        else:
            return queryset.filter(courier=self.value())


class OrderPeriodFilter(admin.SimpleListFilter):
    title = 'Период заказов'
    parameter_name = 'order_period'

    def lookups(self, request, model_admin):
        return (
            ('yesterday', 'Вчера'),
            ('today', 'Сегодня'),
            ('tomorrow', 'Завтра'),
            ('future', 'Будущие заказы'),
        )

    def queryset(self, request, queryset):
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)

        range_gte = request.GET.get('execution_date__range__gte')
        range_lte = request.GET.get('execution_date__range__lte')
        if range_gte and range_lte:
            return queryset

        if self.value() == 'yesterday':
            return queryset.filter(execution_date=yesterday)
        elif self.value() == 'today':
            return queryset.filter(execution_date=today)
        elif self.value() == 'tomorrow':
            return queryset.filter(execution_date=tomorrow)
        elif self.value() == 'future':
            return queryset.filter(execution_date__gt=today)
        return queryset

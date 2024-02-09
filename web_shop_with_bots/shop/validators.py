from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import datetime

def validate_delivery_time(value):
    # Парсим значение времени из строки
    try:
        time_obj = datetime.strptime(value, '%H:%M')
    except ValueError:
        raise ValidationError(_('Неверный формат времени'), code='invalid_time_format')

    # Проверяем, что время находится в диапазоне от 9:30 до 21:30
    min_time = datetime.strptime('09:30', '%H:%M').time()
    max_time = datetime.strptime('21:30', '%H:%M').time()
    if not (min_time <= time_obj.time() <= max_time):
        raise ValidationError(_('Время доставки должно быть от 9:30 до 21:30'), code='invalid_delivery_time')

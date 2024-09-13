from tm_bot.models import MessengerAccount
from django.utils import timezone
from datetime import datetime
from openpyxl import Workbook
from django.http import HttpResponse


def get_filtered_orders_qs(start_date, end_date):
    if start_date is not None and end_date is not None:
        qs = MessengerAccount.objects.filter(
                created__gte=start_date, created__lt=end_date
            )
    else:
        qs = MessengerAccount.objects.all()
    return qs


def export_tm_accounts_to_excel(modeladmin, request, queryset):
    # Получаем текущую дату для включения в имя файла
    current_date = datetime.now(timezone.utc).strftime('%d-%m-%Y')
    filename = f"Tm_accounts_{current_date}.xlsx"
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    start_date = request.GET.get('created__gte')
    end_date = request.GET.get('created__lt')

    queryset = get_filtered_orders_qs(start_date, end_date)

    # Создаем новый Excel-файл
    wb = Workbook()
    ws = wb.active

    ws.title = f"Orders_{current_date}"

    # Заголовки столбцов
    ws.append(['id', 'msngr_type', 'msngr_id', 'tm_chat_id',
               'msngr_username',
               'msngr_first_name', 'msngr_last_name', 'msngr_phone',
               'subscription', 'registered',
               'language',
               'created',
               'notes',
               'msngr_link'
               ])

    # Добавляем данные из queryset
    for obj in queryset:
        ws.append(
            [
                obj.id, obj.msngr_type, obj.msngr_id, obj.tm_chat_id,
                obj.msngr_username, obj.msngr_first_name,
                obj.msngr_last_name, obj.msngr_phone,
                obj.subscription, obj.registered,
                obj.language,
                obj.created.astimezone(None).strftime('%Y-%m-%d %H:%M:%S'),
                obj.notes,
                obj.msngr_link
            ]
        )

    # Сохраняем файл в HttpResponse
    wb.save(response)
    return response


export_tm_accounts_to_excel.short_description = (
    "Сохранить список СОЦ АКК пользователей в Excel.")

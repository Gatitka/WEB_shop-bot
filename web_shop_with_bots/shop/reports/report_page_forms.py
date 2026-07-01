from django import forms


class AdminXlsReportForm(forms.Form):
    REPORT_SHORT = 'short'
    REPORT_FULL = 'full'

    PERIOD_TODAY = 'today'
    PERIOD_YESTERDAY = 'yesterday'
    PERIOD_TOMORROW = 'tomorrow'
    PERIOD_FUTURE = 'future'

    REPORT_CHOICES = (
        (REPORT_SHORT, 'Краткий отчет'),
        (REPORT_FULL, 'Полный отчет'),
    )

    PERIOD_CHOICES = (
        (PERIOD_TODAY, 'Сегодня'),
        (PERIOD_YESTERDAY, 'Вчера'),
        (PERIOD_TOMORROW, 'Завтра'),
        (PERIOD_FUTURE, 'Будущие заказы'),
    )

    report_type = forms.ChoiceField(
        label='Тип отчета',
        choices=REPORT_CHOICES,
        initial=REPORT_SHORT,
        widget=forms.Select(attrs={'class': 'vTextField report-select'}),
    )

    period = forms.ChoiceField(
        label='Быстрый период',
        choices=PERIOD_CHOICES,
        initial=PERIOD_TODAY,
        widget=forms.RadioSelect,
    )

    date_from = forms.DateField(
        label='Дата с',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
        input_formats=['%Y-%m-%d'],
    )
    date_to = forms.DateField(
        label='Дата по',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
        input_formats=['%Y-%m-%d'],
    )

    def clean(self):
        cleaned = super().clean()
        date_from = cleaned.get('date_from')
        date_to = cleaned.get('date_to')

        if bool(date_from) ^ bool(date_to):
            raise forms.ValidationError(
                'Если указываете период вручную, заполните обе даты.'
            )

        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError(
                'Дата начала не может быть позже даты окончания.'
            )

        return cleaned

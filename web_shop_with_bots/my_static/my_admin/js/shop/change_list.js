document.addEventListener('DOMContentLoaded', function () {
    // Существующий код для обработки поля доставки
    const rows = document.querySelectorAll('tr');
    rows.forEach(row => {
        // Удаление выпадающего списка курьеров при самовывозе
        const deliveryTypeField = row.querySelector('td.field-get_delivery_type');
        if (deliveryTypeField) {
            const deliveryType = deliveryTypeField.textContent.trim();
            if (deliveryType === 'takeaway') {
                // Находим td с классом field-courier в текущей строке
                const courierTd = row.querySelector('td.field-courier');
                if (courierTd) {
                    // Заменяем содержимое td на нужный текст или другой элемент
                    courierTd.innerHTML = '';
                }
            }
        }

        // Удаление выбора способа оплаты у партнеров
        // Найти ячейку с источником заказа (field-info) и ячейку с полем выбора способа оплаты (field-payment_type)
        const infoCell = row.querySelector('td.field-info'); // Ячейка с адресом или источником
        // Если обе ячейки существуют и infoCell содержит текст "Glovo"
        if (infoCell && infoCell.textContent.trim() === 'Glovo') {
            const paymentType = row.querySelector('td.field-payment_type'); // Ячейка с выпадающим списком
            if (paymentType) {
                // Удаляем все опции из выпадающего списка
                paymentType.innerHTML = '';
            }
        }
    });

    // Обработка цвета select
    const statusSelects = document.querySelectorAll('td.field-status select');
    statusSelects.forEach(select => {
        // Установка начального цвета
        select.setAttribute('data-selected', select.value);

        // Обновление цвета при изменении
        select.addEventListener('change', function() {
            this.setAttribute('data-selected', this.value);
        });
    });

});

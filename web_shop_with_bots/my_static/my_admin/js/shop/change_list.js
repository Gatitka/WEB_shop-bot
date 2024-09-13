document.addEventListener('DOMContentLoaded', function () {
    const rows = document.querySelectorAll('tr');
    rows.forEach(row => {
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
    });
});

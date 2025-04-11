document.addEventListener('DOMContentLoaded', function() {
    // Функция для получения выбранных блюд
    function getSelectedDishes() {
        var selected = {};
        var dishSelects = document.querySelectorAll('.field-dish select');
        dishSelects.forEach(function(select, index) {
            var value = select.value;
            if (value) {
                if (selected[value]) {
                    selected[value].push(index);
                } else {
                    selected[value] = [index];
                }
            }
        });
        return selected;
    }

    // Функция для очистки полей цены и суммы
    function clearPriceAndAmountFields(selectElement) {
        const row = selectElement.closest('tr');

        // Очищаем поле цены
        const unitPriceField = row.querySelector('.field-unit_price p');
        if (unitPriceField) {
            unitPriceField.textContent = '0.00 ₽';  // Или можно оставить пустым ''
        }

        // Очищаем поле суммы
        const unitAmountField = row.querySelector('.field-unit_amount p');
        if (unitAmountField) {
            unitAmountField.textContent = '0.00';  // Или можно оставить пустым ''
        }

        // Генерируем событие для пересчета общей суммы
        const event = new CustomEvent('amountChanged', {
            detail: { amount: 0 }
        });
        document.dispatchEvent(event)
        updateOrderAmount();
    }

    // Обработчик изменения выбора блюда
    function handleDishChange(event) {
        const changedSelect = event.target;

        // Если выбор блюда сброшен, очищаем соответствующие поля цены и суммы
        if (changedSelect.value === '') {
            clearPriceAndAmountFields(changedSelect);
            return;
        }

        var selected = getSelectedDishes();

        for (var dishId in selected) {
            if (selected[dishId].length > 1) {
                // Блюдо выбрано несколько раз
                alert('Блюдо уже добавлено в заказ. Пожалуйста, измените количество существующей позиции вместо добавления дубликата.');

                // Очищаем последний выбор
                var lastIndex = selected[dishId][selected[dishId].length - 1];
                var lastSelect = document.querySelectorAll('.field-dish select')[lastIndex];

                // Сохраняем ссылку на select перед изменением значения
                const selectToReset = lastSelect;

                // Сбрасываем выбор
                selectToReset.value = '';

                // Очищаем поля цены и суммы
                clearPriceAndAmountFields(selectToReset);
            }
        }
    }

    // Добавляем обработчик события для всех select полей
    document.addEventListener('change', function(event) {
        if (event.target.closest('.field-dish select')) {
            handleDishChange(event);
        }
    });
});

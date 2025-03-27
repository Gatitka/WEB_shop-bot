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

    // Обработчик изменения выбора блюда
    function handleDishChange() {
        var selected = getSelectedDishes();

        for (var dishId in selected) {
            if (selected[dishId].length > 1) {
                // Блюдо выбрано несколько раз
                alert('Блюдо уже добавлено в заказ. Пожалуйста, измените количество существующей позиции вместо добавления дубликата.');
                // Очищаем последний выбор
                var lastIndex = selected[dishId][selected[dishId].length - 1];
                var lastSelect = document.querySelectorAll('.field-dish select')[lastIndex];
                lastSelect.value = '';
            }
        }
    }

    // Добавляем обработчик события для всех select полей
    document.addEventListener('change', function(event) {
        if (event.target.closest('.field-dish select')) {
            handleDishChange();
        }
    });
});

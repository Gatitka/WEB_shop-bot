document.addEventListener('DOMContentLoaded', function() {
    // Создаем объект для хранения уже полученных цен
    var fetchedPrices = {};

    // Функция для массового запроса цен и пересчета unit_amount всех блюд
    function fetchAndUpdateAllPrices() {
        // Получаем все строки таблицы с товарами заказа
        var orderRows = document.querySelectorAll('.dynamic-orderdishes');

        // Перебираем каждую строку таблицы
        orderRows.forEach(function(row) {
            // Извлекаем значение артикула товара и количество
            var dishId = row.querySelector('.field-dish input').value;
            var quantity = row.querySelector('.field-quantity input').value;
            var unitPriceField = row.querySelector('.field-unit_price p');

            // Выполняем AJAX-запрос для получения цены блюда
            fetchAndUpdatePrice(dishId, unitPriceField);

            // Вызываем функцию для пересчета unit_amount
            calculateAmount(row, quantity);
        });

        // Обновляем итоговую сумму заказа
        updateOrderAmount();
    }

    // Вызываем функцию для массового запроса цен и пересчета unit_amount всех блюд при загрузке страницы
    fetchAndUpdateAllPrices();



    // Обработчик события изменения поля выбора блюда
    document.addEventListener('change', function(event) {
        if (event.target && event.target.closest('.field-dish input')) {
            var dishId = event.target.value;
            var unitPriceField = event.target.closest('tr').querySelector('.field-unit_price p');

            // Логирование для проверки
            console.log('Change event fired for dish selection.');

            // Выполняем AJAX-запрос для получения цены блюда
            fetchAndUpdatePrice(dishId, unitPriceField);
        }
    });

    // Обработчик события изменения поля количества
    document.addEventListener('change', function(event) {
        if (event.target && event.target.closest('.field-quantity input')) {
            var unitPriceField = event.target.closest('tr').querySelector('.field-unit_price p');
            calculateAmount(unitPriceField);
        }
    });

    // Функция для вычисления суммы заказа после изменений
    function calculateAmount(unitPriceField) {
        var row = unitPriceField.closest('tr');
        var quantityInput = row.querySelector('.field-quantity input');
        var unitAmountField = row.querySelector('.field-unit_amount p');

        var quantity = parseInt(quantityInput.value, 10);
        var unitPrice = parseFloat(unitPriceField.textContent);

        var unitAmount = quantity * unitPrice;
        unitAmountField.textContent = unitAmount.toFixed(2);

        updateOrderAmount(); // Обновляем сумму заказа
    }

    // Обработчик клика на кнопку "Добавить еще один Товар заказа"
    document.addEventListener('click', function(event) {
        if (event.target && event.target.closest('.add-row a')) {
            // Вызываем функцию для обновления суммы заказа после добавления новой строки
            updateOrderAmount();
        }
    });

    // Функция для обновления суммы заказа
    function updateOrderAmount() {
        var unitAmountFields = document.querySelectorAll('.field-unit_amount p');
        var totalAmount = 0;
        unitAmountFields.forEach(function(field) {
            totalAmount += parseFloat(field.textContent);
        });

        var amountField = document.querySelector('.field-amount .readonly');
        amountField.textContent = totalAmount.toFixed(2);
    }

    // Функция для выполнения AJAX-запроса и обновления цены блюда
    function fetchAndUpdatePrice(dishId, unitPriceField) {
        // Проверяем, была ли уже получена цена для данного блюда
        if (fetchedPrices[dishId]) {
            // Если цена уже получена, обновляем только поле с ценой
            unitPriceField.innerHTML = fetchedPrices[dishId];
            calculateAmount(unitPriceField);
        } else {
            var xhr = new XMLHttpRequest();
            xhr.open('GET', '/api/v1/get_dish_price/?dish_id=' + dishId, true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            xhr.onreadystatechange = function() {
                if (xhr.readyState == 4 && xhr.status == 200) {
                    var response = JSON.parse(xhr.responseText);
                    // Сохраняем полученную цену
                    fetchedPrices[dishId] = response.price;
                    unitPriceField.innerHTML = response.price;
                    calculateAmount(unitPriceField);
                }
            };
            xhr.send();
        }
    }
});

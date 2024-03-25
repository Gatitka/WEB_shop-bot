document.addEventListener('DOMContentLoaded', function() {
    // Получаем кнопку "Рассчитать стоимость доставки"
    var calculateDeliveryButton = document.getElementById('id_calculate_delivery_button');
    if (!calculateDeliveryButton) {
        console.error('Не удалось найти кнопку "Рассчитать стоимость доставки".');
        return;
    }

    // Обработчик события клика на кнопке "Рассчитать стоимость доставки"
    calculateDeliveryButton.addEventListener('click', function() {
        // Получаем значения из полей формы
        var cityElement = document.getElementById('id_city');
        var recipientAddressElement = document.getElementById('id_recipient_address');
        var myRecipientAddressElement = document.getElementById('id_my_recipient_address');
        var discountedAmountElement = document.querySelector('.field-discounted_amount .readonly');
        var deliveryElement = document.querySelector('input[name="delivery"]:checked');

        // Проверяем существование элементов формы
        if (!cityElement || !recipientAddressElement || !discountedAmountElement || !deliveryElement) {
            console.error('Не удалось найти одно или несколько полей формы.');
            return;
        }

        // Получаем значения из элементов формы
        var city = cityElement.value;
        var recipientAddress = recipientAddressElement.value || myRecipientAddressElement.value;
        var discountedAmount = discountedAmountElement.innerText.trim();
        var delivery = deliveryElement.value;

        // Проверяем заполнение всех необходимых полей
        if (!city || !recipientAddress || !discountedAmount || !delivery) {
            console.error('Для расчета стоимости доставки заполните поля город, адрес, сумму заказа и выберите тип доставки.');
            return;
        }

        // Создаем объект данных для отправки на сервер
        var data = {
            city: city,
            recipient_address: recipientAddress,
            discounted_amount: discountedAmount,
            delivery: delivery
        };

        // Формируем данные для отправки на сервер
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'http://127.0.0.1:8000/api/v1/calculate_delivery/', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest'); // Включаем новый заголовок

        xhr.onreadystatechange = function() {
        console.log('Ready state:', xhr.readyState); // Добавляем отладочное сообщение
        console.log('Status:', xhr.status); // Добавляем отладочное сообщение
        if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
        // Парсим ответ сервера
        var response = JSON.parse(xhr.responseText);
        // Обновляем поля формы с полученными данными о зоне доставки и стоимости доставки
        var autoDeliveryZoneElement = document.getElementById('id_auto_delivery_zone');
        var autoDeliveryCostElement = document.getElementById('id_auto_delivery_cost');
        if (autoDeliveryZoneElement) {
            autoDeliveryZoneElement.value = response.auto_delivery_zone;
        }
        if (autoDeliveryCostElement) {
            autoDeliveryCostElement.value = response.auto_delivery_cost;
        }
        } else if (xhr.readyState === XMLHttpRequest.DONE) {
        console.error('Ошибка при выполнении запроса');
        }
        };

        xhr.send(JSON.stringify(data)); // Отправляем данные
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const recipientAddressInput = document.getElementById('id_recipient_address');
    const calculateButton = document.getElementById('calculate_delivery_button');
    const deliverySelect = document.getElementById('id_delivery');
    const amountField = document.querySelector('.field-amount .readonly'); // Изменено поле на '.field-amount .readonly'

    if (recipientAddressInput && calculateButton && deliverySelect && amountField) { // Изменено имя переменной
        recipientAddressInput.addEventListener('input', toggleCalculateButton);
        deliverySelect.addEventListener('change', toggleCalculateButton);
        amountField.addEventListener('input', toggleCalculateButton); // Изменено имя переменной
        toggleCalculateButton(); // Вызываем функцию сразу после загрузки страницы
    }

    function toggleCalculateButton() {
        const recipientAddress = recipientAddressInput.value;
        const deliveryOption = deliverySelect.value;
        const amount = parseFloat(amountField.value); // Изменено имя переменной

        if (recipientAddress && deliveryOption && amount !== 0) { // Изменено имя переменной
            calculateButton.removeAttribute('disabled');
        } else {
            calculateButton.setAttribute('disabled', 'disabled');
        }
    }
});

document.addEventListener('DOMContentLoaded', function() {
    var myDeliveryAddressElement = document.getElementById('id_my_delivery_address');
    var coordinatesElement = document.getElementById('id_coordinates');
    var addressCommentElement = document.getElementById('id_address_comment');

    if (myDeliveryAddressElement && coordinatesElement && addressCommentElement) {
        myDeliveryAddressElement.addEventListener('change', function() {
            var selectedAddress = myDeliveryAddressElement.value;
            var coordinatesDataElement = document.getElementById('id_my_address_coordinates');
            var coordinatesDataString = coordinatesDataElement.value;
            var coordinatesData = JSON.parse(coordinatesDataString);
            var coordinates = coordinatesData[selectedAddress];

            // Устанавливаем координаты в поле coordinates
            coordinatesElement.value = coordinates || '';

            var addressCommentDataElement = document.getElementById('id_my_address_comments');
            var addressCommentDataString = addressCommentDataElement.value;
            var addressCommentData = JSON.parse(addressCommentDataString);
            var addressComment = addressCommentData[selectedAddress];

            // Устанавливаем координаты в поле coordinates
            addressCommentElement.value = addressComment || '';

            const recipientAddressInput = document.querySelector('#id_recipient_address');
            // Получаем только адрес из выбранного варианта
            var addressParts = myDeliveryAddressElement.options[myDeliveryAddressElement.selectedIndex].textContent.split(', кв');
            // Если адрес состоит только из одной части, устанавливаем его как адрес получателя
            if (addressParts.length === 1) {
                recipientAddressInput.value = addressParts[0];
            } else {
                // Иначе, если адрес состоит из нескольких частей, устанавливаем первую часть (без комментария)
                recipientAddressInput.value = addressParts[0];
            }

        });
    }
});


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
        var myDeliveryAddressElement = document.getElementById('id_my_delivery_address');
        var amountField = document.querySelector('.field-amount .readonly'); // Изменено поле на '.field-amount .readonly'
        var deliveryElement = document.querySelector('input[name="delivery"]:checked');
        var coordinatesElement = document.getElementById('id_coordinates'); // Добавлено поле coordinates

        // Получаем элементы для отображения сообщения об ошибке и обновления других полей формы
        var errorMessageElement = document.getElementById('id_error_message');
        var autoDeliveryZoneElement = document.getElementById('id_auto_delivery_zone');
        var autoDeliveryCostElement = document.getElementById('id_auto_delivery_cost');

        // Показать поле ошибки и установить текст ошибки
        function showError(errorMessage) {
            errorMessageElement.value = errorMessage;
            errorMessageElement.style.display = 'block'; // Показать поле ошибки
        }

        // Скрыть поле ошибки
        function hideError() {
            errorMessageElement.value = ''; // Стереть текст ошибки
            errorMessageElement.style.display = 'none'; // Скрыть поле ошибки
        }


        // Проверяем существование элементов формы
        if (!cityElement || !recipientAddressElement || !amountField || !deliveryElement || !coordinatesElement || !autoDeliveryZoneElement || !autoDeliveryCostElement) {
            showError('Не удалось найти одно или несколько полей формы.');
            errorMessageElement.style.display = 'block';
            return;
        }

        // Получаем значения из элементов формы
        var city = cityElement.value;
        var recipientAddress = recipientAddressElement.value || myDeliveryAddressElement.value;
        var amount = amountField.innerText.trim(); // Изменено имя переменной
        var delivery = deliveryElement.value;
        var coordinates = coordinatesElement.value; // Получаем значение поля координат

        // Проверяем, что адрес не пустой
        if (!recipientAddress) {
            showError('Необходимо указать адрес для расчета стоимости доставки.');
            errorMessageElement.style.display = 'block';
            return;
        }

        if (!/\d/.test(recipientAddress)) {
            showError('Адрес должен содержать номер дома для расчета стоимости доставки.');
            return;
        }

        // Проверяем заполнение всех необходимых полей
        if (!city || !amount || !delivery || !recipientAddress) { // Изменено имя переменной
            showError('Для расчета стоимости доставки заполните поля город, сумму заказа и выберите тип доставки.');
            errorMessageElement.style.display = 'block';
            return;
        }

        // Проверяем, что сумма заказа не равна 0,00
        if (parseFloat(amount) === 0.00) { // Изменено имя переменной
            showError('Сумма заказа не может быть равна 0,00 для расчета стоимости доставки.');
            errorMessageElement.style.display = 'block';
            return;
        }

        // Создаем объект данных для отправки на сервер
        var data = {
            city: city,
            recipient_address: recipientAddress,
            amount: amount,
            delivery: delivery,
            coordinates: coordinates // Добавляем поле coordinates
        };

        // Формируем данные для отправки на сервер
        var xhr = new XMLHttpRequest();
        const currentDomain = getCurrentDomain(); // Получаем текущий домен
        let calculateDeliveryUrl;
        if (currentDomain === '127.0.0.1') {
            calculateDeliveryUrl = `http://${currentDomain}:8000/api/v1/calculate_delivery/`;
        } else {
            calculateDeliveryUrl = `https://${currentDomain}/api/v1/calculate_delivery/`;
        }
        xhr.open('POST', calculateDeliveryUrl, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest'); // Включаем новый заголовок

        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                // Парсим ответ сервера
                var response = JSON.parse(xhr.responseText);
                // Обновляем поля формы с полученными данными о зоне доставки, стоимости доставки и координатах
                autoDeliveryZoneElement.value = response.auto_delivery_zone || '';
                autoDeliveryCostElement.value = response.auto_delivery_cost || '';
                hideError()
            } else if (xhr.readyState === XMLHttpRequest.DONE) {
                showError('Ошибка при выполнении запроса');
                errorMessageElement.style.display = 'block';
            }
        };

        xhr.send(JSON.stringify(data)); // Отправляем данные
    });
});

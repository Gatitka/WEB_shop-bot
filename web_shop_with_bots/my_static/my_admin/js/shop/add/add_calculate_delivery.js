// Расчет доставки для формы создания заказа.
// Адрес вводится впервые - расчет запускается автоматически:
// при получении координат, при смене типа заказа на "D", и при загрузке
// страницы, если координаты уже проставлены (например, после ошибки валидации).
//
// Общие calcZoneCost()/applyDeliveryCalcResponse()/buildCalculateDeliveryUrl()
// берутся из delivery_utils.js (подключается раньше этого файла).

document.addEventListener('DOMContentLoaded', function() {
    // Загружаем зоны доставок, переданные Django
    const deliveryZonesDataElement = document.getElementById('delivery_zones-data');
    const deliveryZonesList = deliveryZonesDataElement ? JSON.parse(deliveryZonesDataElement.textContent) : {};
    console.log('Загруженные зоны доставки:', deliveryZonesList);

    // Получаем необходимые элементы формы
    const coordinatesInput = document.getElementById('id_coordinates');
    const amountField = document.querySelector('.field-amount .readonly');
    const deliveryZoneSelect = document.getElementById('id_delivery_zone');
    const deliveryCostInput = document.getElementById('id_delivery_cost');
    const recipientAddressInput = document.getElementById('id_recipient_address');
    const orderTypeField = document.getElementById('id_order_type');

    const errorMessageElement = document.getElementById('id_error_message');
    const autoDeliveryZoneElement = document.getElementById('id_auto_delivery_zone');
    const autoDeliveryCostElement = document.getElementById('id_auto_delivery_cost');

    // Функция для отображения сообщения об ошибке (если элемент существует)
    function showError(errorMessage) {
        console.error("Ошибка:", errorMessage);
        if (errorMessageElement) {
            errorMessageElement.value = errorMessage;
            errorMessageElement.style.display = 'block';
        }
    }

    // Функция для скрытия сообщения об ошибке (если элемент существует)
    function hideError() {
        if (errorMessageElement) {
            errorMessageElement.value = '';
            errorMessageElement.style.display = 'none';
        }
    }

    // Функция для проверки, включена ли доставка (проверяем order_type)
    function isDeliveryEnabled() {
        const orderType = orderTypeField ? orderTypeField.value : '';
        const isDelivery = orderType === 'D';
        console.log("Доставка включена:", isDelivery, "(order_type =", orderType + ")");
        return isDelivery;
    }

    // Пересчет стоимости по уже известной (закэшированной) зоне -
    // используется при ручном выборе зоны и при пересчете только из-за
    // изменения суммы заказа (адрес/координаты не менялись).
    function handleDeliveryZoneChange(isAmountChangeOnly = false) {
        if (!deliveryZoneSelect || !deliveryCostInput || !amountField) return;

        const selectedZoneId = deliveryZoneSelect.value;
        if (!selectedZoneId) return;

        const deliveryZone = deliveryZonesList[selectedZoneId];
        if (!deliveryZone) {
            console.log('Не найдена информация о выбранной зоне доставки');
            return;
        }

        const amount = parseFloat(amountField.textContent) || 0;

        // Зона "по запросу" с уже введенной вручную стоимостью, и пересчет
        // вызван только изменением суммы (не адреса) - сохраняем стоимость
        if (deliveryZone.name === 'по запросу' && isAmountChangeOnly &&
            deliveryCostInput.value && parseFloat(deliveryCostInput.value) > 0) {
            console.log('Зона "по запросу" с уже введенной стоимостью, сохраняем текущую стоимость:', deliveryCostInput.value);
        } else {
            deliveryCostInput.value = calcZoneCost(deliveryZone, amount);
        }

        const event = new CustomEvent('deliveryCostChanged', {
            detail: {
                deliveryCost: parseFloat(deliveryCostInput.value) || 0,
                amount: amount
            }
        });
        document.dispatchEvent(event);
    }

    // Полный расчет через API - для нового/изменившегося адреса
    function calculateDelivery() {
        console.log("Вызов функции calculateDelivery()");

        if (!isDeliveryEnabled()) {
            console.log('Доставка отключена, расчет не выполняется');
            return;
        }
        if (!coordinatesInput || !coordinatesInput.value) {
            console.log('Координаты отсутствуют, расчет не выполняется');
            return;
        }
        if (!amountField) {
            console.log('Поле суммы не найдено, расчет не выполняется');
            return;
        }
        if (!deliveryZoneSelect) {
            console.log('Поле выбора зоны доставки не найдено, расчет не выполняется');
            return;
        }

        const coordinates = coordinatesInput.value;
        const amount = parseFloat(amountField.textContent) || 0;
        const city = getOrderCity();
        if (!city) {
            console.error('Не удалось определить город заказа (поле city) - расчет доставки невозможен.');
            showError('Не удалось определить город заказа для расчета доставки.');
            return;
        }
        const recipientAddress = recipientAddressInput ? recipientAddressInput.value : '';

        // "delivery: true" - бэкенд сам находит Delivery(city=city, type='delivery')
        const data = {
            city: city,
            recipient_address: recipientAddress,
            amount: amount,
            delivery: true,
            coordinates: coordinates
        };

        console.log("Данные для запроса:", data);

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        fetch(buildCalculateDeliveryUrl(), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Ошибка при выполнении запроса на расчет доставки: ${response.status}`);
            }
            return response.json();
        })
        .then(response => {
            console.log('Получен ответ с расчетом доставки:', response);

            const newCost = applyDeliveryCalcResponse(response, {
                deliveryZoneSelect, deliveryCostInput,
                autoDeliveryZoneElement, autoDeliveryCostElement
            });

            if (newCost !== null) {
                const event = new CustomEvent('deliveryCostChanged', {
                    detail: { deliveryCost: newCost, amount: amount }
                });
                document.dispatchEvent(event);
            }

            hideError();
        })
        .catch(error => {
            console.error("Ошибка при расчете доставки:", error);
            showError(error.message);
        });
    }

    // Отслеживаем изменение координат (событие от address_autocomplete.js)
    if (coordinatesInput) {
        document.addEventListener('coordinatesChanged', function(event) {
            console.log("Получено событие coordinatesChanged:", event.detail);

            if (event.detail && event.detail.coordinates) {
                if (isDeliveryEnabled()) {
                    console.log("Запуск calculateDelivery() из обработчика coordinatesChanged");
                    calculateDelivery();
                } else {
                    console.log("Доставка отключена, calculateDelivery() не вызывается");
                }
            }
        });
    }

    // Слушаем изменение суммы заказа для пересчета промо-условий доставки
    document.addEventListener('amountChanged', function(event) {
        if (isDeliveryEnabled() && deliveryZoneSelect && deliveryZoneSelect.value) {
            console.log('Получено событие изменения суммы, пересчитываем стоимость доставки:', event.detail);
            handleDeliveryZoneChange(true);
        }
    });

    // Отслеживаем изменение типа заказа
    if (orderTypeField) {
        orderTypeField.addEventListener('change', function() {
            console.log("Изменение типа заказа на:", this.value);
            const isDelivery = this.value === 'D';

            if (isDelivery && coordinatesInput && coordinatesInput.value) {
                console.log("Тип заказа изменен на 'D' (доставка), запуск calculateDelivery()");
                calculateDelivery();
            }
        });
    }

    // Если при загрузке страницы уже есть координаты и доставка включена
    if (coordinatesInput && coordinatesInput.value && isDeliveryEnabled()) {
        console.log("Запуск calculateDelivery() при загрузке страницы");
        calculateDelivery();
    }

    // Обработчик ручного изменения зоны доставки
    if (deliveryZoneSelect) {
        deliveryZoneSelect.addEventListener('change', function() {
            console.log('Изменена зона доставки:', this.value);
            handleDeliveryZoneChange(false);
        });
    }
});

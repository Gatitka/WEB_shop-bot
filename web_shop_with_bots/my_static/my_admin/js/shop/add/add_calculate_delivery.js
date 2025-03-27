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

    // Проверяем существование элементов (опционально)
    const errorMessageElement = document.getElementById('id_error_message');
    const autoDeliveryZoneElement = document.getElementById('id_auto_delivery_zone');
    const autoDeliveryCostElement = document.getElementById('id_auto_delivery_cost');

    // Функция для получения текущего домена
    function getCurrentDomain() {
        return window.location.hostname;
    }

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

    // Функция для проверки, включена ли доставка (теперь проверяем order_type)
    function isDeliveryEnabled() {
        const orderType = orderTypeField ? orderTypeField.value : '';
        const isDelivery = orderType === 'D';
        console.log("Доставка включена:", isDelivery, "(order_type =", orderType + ")");
        return isDelivery;
    }

    // Функция для обработки изменения зоны доставки (от API или вручную)
    function handleDeliveryZoneChange(isAmountChangeOnly = false) {
        if (!deliveryZoneSelect || !deliveryCostInput || !amountField) return;

        const selectedZoneId = deliveryZoneSelect.value;
        if (!selectedZoneId || selectedZoneId === '') return;

        // Получаем данные зоны доставки из загруженного списка зон
        const deliveryZone = deliveryZonesList[selectedZoneId];
        if (!deliveryZone) {
            console.log('Не найдена информация о выбранной зоне доставки');
            return;
        }

        console.log('Проверка промо-условий для зоны доставки:', deliveryZone);

        // Если зона "по запросу" и вызов произошел только из-за изменения суммы (а не адреса)
        // и стоимость доставки уже введена, то сохраняем текущее значение
        if (deliveryZone.name === 'по запросу' && isAmountChangeOnly &&
            deliveryCostInput.value && parseFloat(deliveryCostInput.value) > 0) {
            console.log('Зона "по запросу" с уже введенной стоимостью, сохраняем текущую стоимость:', deliveryCostInput.value);
        }
        // В остальных случаях применяем стандартную логику
        else {
            // Проверяем, есть ли у зоны промо-условие
            if (deliveryZone.is_promo) {
                const amount = parseFloat(amountField.textContent) || 0;

                console.log('Сумма заказа:', amount);
                console.log('Минимальная сумма для бесплатной доставки:', deliveryZone.promo_min_order_amount);

                // Если сумма заказа больше или равна минимальной сумме для промо
                if (amount >= deliveryZone.promo_min_order_amount) {
                    deliveryCostInput.value = '0';
                    console.log('Применена бесплатная доставка (промо-условие)');
                } else {
                    deliveryCostInput.value = deliveryZone.delivery_cost;
                    console.log('Установлена стандартная стоимость доставки:', deliveryZone.delivery_cost);
                }
            } else {
                // Для непромо-зон всегда устанавливаем стандартную стоимость доставки
                deliveryCostInput.value = deliveryZone.delivery_cost;
                console.log('Установлена стандартная стоимость доставки (непромо-зона):', deliveryZone.delivery_cost);
            }
        }

        // Генерируем событие изменения стоимости доставки
        const event = new CustomEvent('deliveryCostChanged', {
            detail: {
                deliveryCost: parseFloat(deliveryCostInput.value),
                amount: parseFloat(amountField.textContent) || 0
            }
        });
        document.dispatchEvent(event);
    }

    // Функция для автоматического расчета доставки
    function calculateDelivery() {
        console.log("Вызов функции calculateDelivery()");

        // Проверяем, включена ли доставка
        if (!isDeliveryEnabled()) {
            console.log('Доставка отключена, расчет не выполняется');
            return;
        }

        // Проверяем наличие необходимых данных и элементов
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

        // Получаем необходимые значения
        const coordinates = coordinatesInput.value;
        const amount = parseFloat(amountField.textContent) || 0;

        console.log("Данные для расчета: координаты =", coordinates, ", сумма =", amount);

        const cityElement = document.getElementById('id_city');
        const city = cityElement ? cityElement.value : 'Beograd';
        const recipientAddress = recipientAddressInput ? recipientAddressInput.value : '';

        // Создаем данные для запроса
        const data = {
            city: city,
            recipient_address: recipientAddress,
            amount: amount,
            delivery: true,
            coordinates: coordinates
        };

        console.log("Данные для запроса:", data);

        // Формируем URL для запроса
        const currentDomain = getCurrentDomain();
        let calculateDeliveryUrl;
        if (currentDomain === '127.0.0.1') {
            calculateDeliveryUrl = `http://${currentDomain}:8000/api/v1/calculate_delivery/`;
        } else {
            calculateDeliveryUrl = `https://${currentDomain}/api/v1/calculate_delivery/`;
        }

        console.log("URL для запроса:", calculateDeliveryUrl);

        // Получаем CSRF-токен
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        console.log("Отправка запроса на расчет доставки...");

        // Выполняем запрос
        fetch(calculateDeliveryUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            console.log("Получен ответ от сервера, статус:", response.status);
            if (!response.ok) {
                throw new Error(`Ошибка при выполнении запроса на расчет доставки: ${response.status}`);
            }
            return response.json();
        })
        .then(response => {
            console.log('Получен ответ с расчетом доставки:', response);

            // Обновляем скрытые поля (если они существуют)
            if (autoDeliveryZoneElement) {
                autoDeliveryZoneElement.value = response.auto_delivery_zone || '';
            }

            if (autoDeliveryCostElement) {
                autoDeliveryCostElement.value = response.auto_delivery_cost || '';
            }

            // Обновляем выбор зоны доставки по ID
            if (deliveryZoneSelect && response.auto_delivery_zone_id) {
                console.log("Устанавливаем зону доставки по ID:", response.auto_delivery_zone_id);

                let zoneFound = false;
                for (let i = 0; i < deliveryZoneSelect.options.length; i++) {
                    // Сравниваем value опции с ID зоны доставки
                    if (deliveryZoneSelect.options[i].value == response.auto_delivery_zone_id) {
                        console.log(`Найдена опция с ID ${response.auto_delivery_zone_id}, индекс: ${i}`);
                        deliveryZoneSelect.selectedIndex = i;
                        zoneFound = true;
                        break;
                    }
                }

                // Если зона найдена, то handleDeliveryZoneChange() будет вызван через обработчик события 'change'
                // Искусственно запускаем событие change
                if (zoneFound) {
                    deliveryZoneSelect.dispatchEvent(new Event('change'));
                }
            }
            // Запасной вариант - поиск по имени зоны
            else if (deliveryZoneSelect && response.auto_delivery_zone) {
                console.log("Ищем зону доставки по имени:", response.auto_delivery_zone);

                let zoneFound = false;
                for (let i = 0; i < deliveryZoneSelect.options.length; i++) {
                    const option = deliveryZoneSelect.options[i];
                    const optionText = option.text.trim();

                    if (optionText === response.auto_delivery_zone ||
                        optionText.startsWith(response.auto_delivery_zone + ',')) {
                        console.log(`Найдена опция по имени '${response.auto_delivery_zone}', индекс: ${i}`);
                        deliveryZoneSelect.selectedIndex = i;
                        zoneFound = true;
                        break;
                    }
                }

                // Если зона найдена, то handleDeliveryZoneChange() будет вызван через обработчик события 'change'
                // Искусственно запускаем событие change
                if (zoneFound) {
                    deliveryZoneSelect.dispatchEvent(new Event('change'));
                }
            }

            hideError();
        })
        .catch(error => {
            console.error("Ошибка при расчете доставки:", error);
            showError(error.message);
        });
    }

    // Отслеживаем изменение координат
    if (coordinatesInput) {
        // Слушаем событие coordinatesChanged из address_autocomplete.js
        document.addEventListener('coordinatesChanged', function(event) {
            console.log("Получено событие coordinatesChanged:", event.detail);

            if (event.detail && event.detail.coordinates) {
                console.log("Получены координаты:", event.detail.coordinates);

                const deliveryEnabled = isDeliveryEnabled();
                console.log("Доставка включена:", deliveryEnabled);

                if (deliveryEnabled) {
                    console.log("Запуск calculateDelivery() из обработчика coordinatesChanged");
                    calculateDelivery();
                } else {
                    console.log("Доставка отключена, calculateDelivery() не вызывается");
                }
            } else {
                console.log("Нет координат в событии coordinatesChanged");
            }
        });
    }

    // Слушаем изменение суммы заказа для пересчета промо-условий доставки
    document.addEventListener('amountChanged', function(event) {
        if (isDeliveryEnabled() && deliveryZoneSelect && deliveryZoneSelect.value) {
            console.log('Получено событие изменения суммы, пересчитываем стоимость доставки:', event.detail);
            // Передаем флаг, что изменилась только сумма заказа
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

    // Если при загрузке страницы уже есть координаты и доставка включена, выполняем расчет
    if (coordinatesInput && coordinatesInput.value && isDeliveryEnabled()) {
        console.log("Запуск calculateDelivery() при загрузке страницы");
        calculateDelivery();
    }

    // Обработчик изменения зоны доставки
    if (deliveryZoneSelect) {
        deliveryZoneSelect.addEventListener('change', function() {
            console.log('Изменена зона доставки:', this.value);
            // При прямом изменении зоны доставки всегда обновляем стоимость (false - не только сумма изменилась)
            handleDeliveryZoneChange(false);
        });
    }
});

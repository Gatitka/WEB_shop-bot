// Расчет доставки для формы изменения заказа.
// В отличие от add-формы, ничего не пересчитывается автоматически при
// открытии формы - показывается то, что уже есть в заказе. Полный пересчет
// (обращение к API с адресом/координатами) запускается только вручную,
// по кнопке "Рассчитать". Пересчет по уже выбранной зоне (при смене суммы
// или ручном выборе зоны) - единственное, что происходит автоматически.
//
// Общие calcZoneCost()/applyDeliveryCalcResponse()/buildCalculateDeliveryUrl()
// берутся из delivery_utils.js (подключается раньше этого файла).

document.addEventListener('DOMContentLoaded', function() {
    const deliveryZonesDataElement = document.getElementById('delivery_zones-data');
    const deliveryZonesList = deliveryZonesDataElement ? JSON.parse(deliveryZonesDataElement.textContent) : {};
    console.log('Загруженные зоны доставки:', deliveryZonesList);

    // Получаем необходимые элементы формы
    const recipientAddressInput = document.getElementById('id_recipient_address');
    const calculateButton = document.querySelector('.fieldBox.field-calculate_delivery_button');
    const orderTypeField = document.getElementById('id_order_type');
    const amountField = document.querySelector('.field-amount .readonly');
    const deliveryCostInput = document.getElementById('id_delivery_cost');
    const autoDeliveryCostInput = document.getElementById('id_auto_delivery_cost');
    const coordinatesInput = document.getElementById('id_coordinates');
    const deliveryZoneSelect = document.getElementById('id_delivery_zone');
    const errorMessageElement = document.getElementById('id_error_message');
    const autoDeliveryZoneElement = document.getElementById('id_auto_delivery_zone');

    console.log('Form elements check:', {
        recipientAddressInput: !!recipientAddressInput,
        calculateButton: !!calculateButton,
        orderTypeField: !!orderTypeField,
        amountField: !!amountField,
        deliveryCostInput: !!deliveryCostInput,
        autoDeliveryCostInput: !!autoDeliveryCostInput,
        coordinatesInput: !!coordinatesInput,
        deliveryZoneSelect: !!deliveryZoneSelect,
        errorMessageElement: !!errorMessageElement,
        autoDeliveryZoneElement: !!autoDeliveryZoneElement
    });

    // Функция для проверки, включена ли доставка (проверяем order_type -
    // поле "тип доставки" id_delivery убрано из формы изменения заказа)
    function isDeliveryEnabled() {
        const orderType = orderTypeField ? orderTypeField.value : '';
        const isDelivery = orderType === 'D';
        console.log("Доставка включена:", isDelivery, "(order_type =", orderType + ")");
        return isDelivery;
    }

    // Функция для отправки события об изменении стоимости доставки
    function triggerDeliveryCostChangedEvent(deliveryCost) {
        const event = new CustomEvent('deliveryCostChanged', {
            detail: { deliveryCost: deliveryCost }
        });
        document.dispatchEvent(event);
        console.log('deliveryCostChanged event dispatched with cost:', deliveryCost);
    }

    // Функция для отображения/скрытия сообщения об ошибке
    function showError(errorMessage) {
        if (errorMessageElement) {
            console.warn('Error message:', errorMessage);
            errorMessageElement.value = errorMessage;
            errorMessageElement.style.display = 'block';
        } else {
            console.error('Error message element not found, error:', errorMessage);
        }
    }

    function hideError() {
        if (errorMessageElement) {
            errorMessageElement.value = '';
            errorMessageElement.style.display = 'none';
        }
    }

    // Активация/деактивация кнопки расчета доставки
    function toggleCalculateButton() {
        if (!calculateButton) return;

        const recipientAddress = recipientAddressInput?.value;
        const amount = parseFloat(amountField?.textContent || '0');

        if (recipientAddress && isDeliveryEnabled() && amount !== 0) {
            calculateButton.removeAttribute('disabled');
        } else {
            calculateButton.setAttribute('disabled', 'disabled');
        }
    }

    // Обработка изменения поля my_delivery_address
    const myDeliveryAddressElement = document.getElementById('id_my_delivery_address');
    if (myDeliveryAddressElement && coordinatesInput) {
        myDeliveryAddressElement.addEventListener('change', function() {
            console.log('My delivery address changed');
            var selectedAddress = myDeliveryAddressElement.value;
            var coordinatesDataElement = document.getElementById('id_my_address_coordinates');

            if (!coordinatesDataElement) {
                console.warn('Coordinates data element not found');
                return;
            }

            try {
                var coordinatesDataString = coordinatesDataElement.value;
                var coordinatesData = JSON.parse(coordinatesDataString);
                var coordinates = coordinatesData[selectedAddress];

                coordinatesInput.value = coordinates || '';
                console.log('Coordinates set to:', coordinates);

                var addressCommentElement = document.getElementById('id_address_comment');
                var addressCommentDataElement = document.getElementById('id_my_address_comments');

                if (addressCommentElement && addressCommentDataElement) {
                    var addressCommentDataString = addressCommentDataElement.value;
                    var addressCommentData = JSON.parse(addressCommentDataString);
                    var addressComment = addressCommentData[selectedAddress];
                    addressCommentElement.value = addressComment || '';
                    addressCommentElement.dispatchEvent(new Event('change'));
                }

                const recipientAddressInput = document.querySelector('#id_recipient_address');
                if (recipientAddressInput && myDeliveryAddressElement.selectedIndex >= 0) {
                    var addressParts = myDeliveryAddressElement.options[myDeliveryAddressElement.selectedIndex].textContent.split(', кв');
                    recipientAddressInput.value = addressParts[0];
                }

                toggleCalculateButton();

                const event = new CustomEvent('coordinatesChanged', {
                    detail: { coordinates: coordinates }
                });
                document.dispatchEvent(event);
            } catch (e) {
                console.error('Error processing address data:', e);
                showError('Ошибка при обработке данных адреса: ' + e.message);
            }
        });
    }

    // Пересчет стоимости по уже известной (закэшированной) зоне -
    // используется при ручном выборе зоны и при пересчете только из-за
    // изменения суммы заказа (адрес/координаты не менялись, кнопка "Рассчитать"
    // не нажималась).
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

        triggerDeliveryCostChangedEvent(parseFloat(deliveryCostInput.value) || 0);
    }

    // Обработчик нажатия на кнопку расчета доставки - единственная точка входа
    // в полный расчет через API в этой форме (контролируемый пересчет)
    if (calculateButton) {
        calculateButton.addEventListener('click', function() {
            console.log('Calculate delivery button clicked');

            const city = getOrderCity();
            const city = cityField ? cityField.textContent.trim() : '';
            const recipientAddress = recipientAddressInput?.value || myDeliveryAddressElement?.value;
            const amount = amountField?.textContent?.trim();
            const coordinates = coordinatesInput?.value;

            console.log('Delivery calculation inputs:', {
                city: city, recipientAddress: recipientAddress,
                amount: amount, coordinates: coordinates
            });

            if (!recipientAddress) {
                showError('Необходимо указать адрес для расчета стоимости доставки.');
                return;
            }
            if (!/\d/.test(recipientAddress)) {
                showError('Адрес должен содержать номер дома для расчета стоимости доставки.');
                return;
            }
            if (!isDeliveryEnabled()) {
                showError('Для расчета стоимости доставки выберите тип заказа "Доставка".');
                return;
            }
            if (!city || !amount) {
                showError('Для расчета стоимости доставки заполните поля город и сумму заказа.');
                return;
            }
            if (parseFloat(amount) === 0.00) {
                showError('Сумма заказа не может быть равна 0,00 для расчета стоимости доставки.');
                return;
            }

            // "delivery: true" - бэкенд сам находит Delivery(city=city, type='delivery')
            const data = {
                city: city,
                recipient_address: recipientAddress,
                amount: amount,
                delivery: true,
                coordinates: coordinates
            };

            console.log('Sending delivery calculation request with data:', data);

            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
            const xhr = new XMLHttpRequest();

            xhr.open('POST', buildCalculateDeliveryUrl(), true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            if (csrfToken) {
                xhr.setRequestHeader('X-CSRFToken', csrfToken);
            }

            xhr.onreadystatechange = function() {
                if (xhr.readyState === XMLHttpRequest.DONE) {
                    console.log('XHR request completed with status:', xhr.status);

                    if (xhr.status === 200) {
                        try {
                            if (!xhr.responseText || xhr.responseText.trim() === '') {
                                throw new Error('Получен пустой ответ от сервера');
                            }

                            var response = JSON.parse(xhr.responseText);
                            console.log('API response received:', response);

                            const newCost = applyDeliveryCalcResponse(response, {
                                deliveryZoneSelect, deliveryCostInput,
                                autoDeliveryZoneElement,
                                autoDeliveryCostElement: autoDeliveryCostInput
                            });

                            if (newCost !== null) {
                                triggerDeliveryCostChangedEvent(newCost);
                            }

                            hideError();
                        } catch (e) {
                            console.error('Error parsing API response:', e, 'Response text:', xhr.responseText);
                            showError('Ошибка при обработке ответа сервера: ' + e.message);
                        }
                    } else {
                        console.error('API request error:', xhr.status, xhr.statusText, 'Response:', xhr.responseText);
                        try {
                            const errorResponse = JSON.parse(xhr.responseText);
                            showError('Ошибка при выполнении запроса: ' + (errorResponse.error || xhr.status));
                        } catch (e) {
                            showError('Ошибка при выполнении запроса: ' + xhr.status);
                        }
                    }
                }
            };

            xhr.onerror = function() {
                console.error('Network error occurred during API request');
                showError('Ошибка сети при выполнении запроса');
            };

            xhr.ontimeout = function() {
                console.error('API request timeout');
                showError('Превышено время ожидания ответа от сервера');
            };

            xhr.timeout = 15000; // 15 секунд

            try {
                const jsonData = JSON.stringify(data);
                console.log('Sending JSON data:', jsonData);
                xhr.send(jsonData);
            } catch (e) {
                console.error('Error sending request:', e);
                showError('Ошибка при отправке запроса: ' + e.message);
            }
        });
    }

    // Отслеживаем изменения в полях формы, влияющих на доступность кнопки
    if (recipientAddressInput) {
        recipientAddressInput.addEventListener('input', toggleCalculateButton);
    }
    if (orderTypeField) {
        orderTypeField.addEventListener('change', toggleCalculateButton);
    }
    if (amountField) {
        amountField.addEventListener('input', toggleCalculateButton);
    }

    // Отслеживание изменений поля стоимости доставки
    if (deliveryCostInput) {
        ['input', 'change', 'blur'].forEach(function(eventType) {
            deliveryCostInput.addEventListener(eventType, function() {
                console.log(`Delivery cost ${eventType} event:`, this.value);
                triggerDeliveryCostChangedEvent(parseFloat(this.value) || 0);
            });
        });
    }

    // То же самое для auto_delivery_cost
    if (autoDeliveryCostInput) {
        ['input', 'change', 'blur'].forEach(function(eventType) {
            autoDeliveryCostInput.addEventListener(eventType, function() {
                console.log(`Auto delivery cost ${eventType} event:`, this.value);
                triggerDeliveryCostChangedEvent(parseFloat(this.value) || 0);
            });
        });
    }

    // Инициализация при загрузке страницы
    toggleCalculateButton();

    // Обработчик ручного изменения зоны доставки
    if (deliveryZoneSelect) {
        deliveryZoneSelect.addEventListener('change', function() {
            console.log('Изменена зона доставки:', this.value);
            handleDeliveryZoneChange(false);
        });
    }

    // Слушаем изменение суммы заказа для пересчета промо-условий доставки
    // по уже выбранной зоне (без обращения к API - контролируемый пересчет
    // в этой форме предполагает, что полный расчет запускается только кнопкой)
    document.addEventListener('amountChanged', function(event) {
        if (isDeliveryEnabled() && deliveryZoneSelect && deliveryZoneSelect.value) {
            console.log('Получено событие изменения суммы, пересчитываем стоимость доставки:', event.detail);
            handleDeliveryZoneChange(true);
        }
    });

    console.log('Delivery calculation script initialization complete');
});

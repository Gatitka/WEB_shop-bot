document.addEventListener('DOMContentLoaded', function() {
    const deliveryZonesDataElement = document.getElementById('delivery_zones-data');
    const deliveryZonesList = deliveryZonesDataElement ? JSON.parse(deliveryZonesDataElement.textContent) : {};

    console.log('Загруженные зоны доставки:', deliveryZonesList);

    // Получаем необходимые элементы формы
    const recipientAddressInput = document.getElementById('id_recipient_address');
    const calculateButton = document.querySelector('.fieldBox.field-calculate_delivery_button');
    const deliverySelect = document.querySelector('input[name="delivery"]:checked');
    const amountField = document.querySelector('.field-amount .readonly');
    const deliveryCostInput = document.getElementById('id_delivery_cost');
    const autoDeliveryCostInput = document.getElementById('id_auto_delivery_cost');
    const coordinatesInput = document.getElementById('id_coordinates');
    const deliveryZoneSelect = document.getElementById('id_delivery_zone');
    //const errorMessageElement = document.querySelector('.fieldBox.field-error_message');
    const errorMessageElement = document.getElementById('id_error_message');
    const autoDeliveryZoneElement = document.getElementById('id_auto_delivery_zone');

    // Проверяем наличие элементов формы
    console.log('Form elements check:', {
        recipientAddressInput: !!recipientAddressInput,
        calculateButton: !!calculateButton,
        deliverySelect: !!deliverySelect,
        amountField: !!amountField,
        deliveryCostInput: !!deliveryCostInput,
        autoDeliveryCostInput: !!autoDeliveryCostInput,
        coordinatesInput: !!coordinatesInput,
        deliveryZoneSelect: !!deliveryZoneSelect,
        errorMessageElement: !!errorMessageElement,
        autoDeliveryZoneElement: !!autoDeliveryZoneElement
    });

    // Функция для получения текущего домена
    function getCurrentDomain() {
        return window.location.hostname;
    }

    // Функция для отправки события об изменении стоимости доставки
    function triggerDeliveryCostChangedEvent(deliveryCost) {
        // Генерируем событие изменения стоимости доставки для других скриптов
        const event = new CustomEvent('deliveryCostChanged', {
            detail: {
                deliveryCost: deliveryCost
            }
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
        const deliveryOption = document.querySelector('input[name="delivery"]:checked');
        const amount = parseFloat(amountField?.textContent || '0');

        if (recipientAddress && deliveryOption && amount !== 0) {
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

                // Устанавливаем координаты в поле coordinates
                coordinatesInput.value = coordinates || '';
                console.log('Coordinates set to:', coordinates);

                // Обновляем комментарий к адресу
                var addressCommentElement = document.getElementById('id_address_comment');
                var addressCommentDataElement = document.getElementById('id_my_address_comments');

                if (addressCommentElement && addressCommentDataElement) {
                    var addressCommentDataString = addressCommentDataElement.value;
                    var addressCommentData = JSON.parse(addressCommentDataString);
                    var addressComment = addressCommentData[selectedAddress];
                    addressCommentElement.value = addressComment || '';
                }

                // Обновляем поле адреса получателя
                const recipientAddressInput = document.querySelector('#id_recipient_address');
                if (recipientAddressInput && myDeliveryAddressElement.selectedIndex >= 0) {
                    var addressParts = myDeliveryAddressElement.options[myDeliveryAddressElement.selectedIndex].textContent.split(', кв');
                    recipientAddressInput.value = addressParts[0];
                }

                // Обновляем кнопку расчета
                toggleCalculateButton();

                // Если координаты изменились, отправляем событие
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

    // Функция для обработки изменения зоны доставки (от API или вручную)
    function handleDeliveryZoneChange() {
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

        // Генерируем событие изменения стоимости доставки
        const event = new CustomEvent('deliveryCostChanged', {
            detail: {
                deliveryCost: parseFloat(deliveryCostInput.value),
                amount: parseFloat(amountField.textContent) || 0
            }
        });
        document.dispatchEvent(event);
    }

    // Обработчик нажатия на кнопку расчета доставки
    if (calculateButton) {
        calculateButton.addEventListener('click', function() {
            console.log('Calculate delivery button clicked');

            // Получаем и проверяем необходимые значения
            const city = document.getElementById('id_city')?.value;
            const recipientAddress = recipientAddressInput?.value || myDeliveryAddressElement?.value;
            const amount = amountField?.textContent?.trim();
            const deliveryInput = document.querySelector('input[name="delivery"]:checked');
            const delivery = deliveryInput ? deliveryInput.value : undefined;
            const coordinates = coordinatesInput?.value;

            console.log('Delivery calculation inputs:', {
                city: city,
                recipientAddress: recipientAddress,
                amount: amount,
                delivery: delivery,
                coordinates: coordinates
            });

            // Проверяем необходимые поля
            if (!recipientAddress) {
                showError('Необходимо указать адрес для расчета стоимости доставки.');
                return;
            }

            if (!/\d/.test(recipientAddress)) {
                showError('Адрес должен содержать номер дома для расчета стоимости доставки.');
                return;
            }

            if (!city || !amount || !delivery) {
                showError('Для расчета стоимости доставки заполните поля город, сумму заказа и выберите тип доставки.');
                return;
            }

            if (parseFloat(amount) === 0.00) {
                showError('Сумма заказа не может быть равна 0,00 для расчета стоимости доставки.');
                return;
            }

            // Создаем объект данных для отправки на сервер
            const data = {
                city: city,
                recipient_address: recipientAddress,
                amount: amount,
                delivery: delivery,
                coordinates: coordinates
            };

            console.log('Sending delivery calculation request with data:', data);

            // Получаем CSRF-токен (если требуется)
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

            // Формируем данные для отправки на сервер
            const xhr = new XMLHttpRequest();
            const currentDomain = getCurrentDomain();
            let calculateDeliveryUrl;
            if (currentDomain === '127.0.0.1') {
                calculateDeliveryUrl = `http://${currentDomain}:8000/api/v1/calculate_delivery/`;
            } else {
                calculateDeliveryUrl = `https://${currentDomain}/api/v1/calculate_delivery/`;
            }

            xhr.open('POST', calculateDeliveryUrl, true);
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
                            // Проверяем не пустой ли ответ
                            if (!xhr.responseText || xhr.responseText.trim() === '') {
                                throw new Error('Получен пустой ответ от сервера');
                            }

                            // Парсим ответ сервера
                            var response = JSON.parse(xhr.responseText);
                            console.log('API response received:', response);

                            // Обновляем поля формы с полученными данными
                            if (autoDeliveryZoneElement) {
                                autoDeliveryZoneElement.value = response.auto_delivery_zone || '';
                                console.log('Auto delivery zone set to:', response.auto_delivery_zone);
                            }

                            if (autoDeliveryCostInput) {
                                autoDeliveryCostInput.value = response.auto_delivery_cost || '';
                                console.log('Auto delivery cost set to:', response.auto_delivery_cost);
                            }

                            // Если в ответе есть ID зоны доставки, обновляем dropdown
                            if (deliveryZoneSelect && response.auto_delivery_zone_id) {
                                console.log('Setting delivery zone select to ID:', response.auto_delivery_zone_id);
                                for (let i = 0; i < deliveryZoneSelect.options.length; i++) {
                                    if (deliveryZoneSelect.options[i].value == response.auto_delivery_zone_id) {
                                        deliveryZoneSelect.selectedIndex = i;
                                        console.log('Delivery zone select option found at index:', i);

                                        // Отправляем событие изменения
                                        const changeEvent = new Event('change');
                                        deliveryZoneSelect.dispatchEvent(changeEvent);
                                        break;
                                    }
                                }
                            }

                            // Если есть auto_delivery_cost, копируем его в поле delivery_cost
                            if (deliveryCostInput && response.auto_delivery_cost) {
                                deliveryCostInput.value = response.auto_delivery_cost;
                                console.log('Delivery cost set to:', response.auto_delivery_cost);

                                // Отправляем событие изменения стоимости доставки
                                triggerDeliveryCostChangedEvent(parseFloat(response.auto_delivery_cost));

                                // Отправляем событие изменения
                                const changeEvent = new Event('change');
                                deliveryCostInput.dispatchEvent(changeEvent);
                            }

                            hideError();
                        } catch (e) {
                            console.error('Error parsing API response:', e, 'Response text:', xhr.responseText);
                            showError('Ошибка при обработке ответа сервера: ' + e.message);
                        }
                    } else {
                        console.error('API request error:', xhr.status, xhr.statusText, 'Response:', xhr.responseText);
                        try {
                            // Попытка прочитать ответ как JSON-ошибку
                            const errorResponse = JSON.parse(xhr.responseText);
                            showError('Ошибка при выполнении запроса: ' + (errorResponse.error || xhr.status));
                        } catch (e) {
                            // Если не получилось распарсить, показываем общую ошибку
                            showError('Ошибка при выполнении запроса: ' + xhr.status);
                        }
                    }
                }
            };

            // Добавляем обработчики событий для отслеживания прогресса и ошибок
            xhr.onerror = function() {
                console.error('Network error occurred during API request');
                showError('Ошибка сети при выполнении запроса');
            };

            xhr.ontimeout = function() {
                console.error('API request timeout');
                showError('Превышено время ожидания ответа от сервера');
            };

            // Устанавливаем таймаут
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

    // Отслеживаем изменения в полях формы, влияющих на расчет
    if (recipientAddressInput) {
        recipientAddressInput.addEventListener('input', toggleCalculateButton);
    }

    if (deliverySelect) {
        deliverySelect.addEventListener('change', toggleCalculateButton);
    }

    if (amountField) {
        amountField.addEventListener('input', toggleCalculateButton);
    }

    // Отслеживание изменений поля стоимости доставки
    if (deliveryCostInput) {
        console.log('Adding event listeners to delivery cost input');

        ['input', 'change', 'blur'].forEach(function(eventType) {
            deliveryCostInput.addEventListener(eventType, function() {
                console.log(`Delivery cost ${eventType} event:`, this.value);
                // Отправляем событие изменения стоимости доставки
                triggerDeliveryCostChangedEvent(parseFloat(this.value) || 0);
            });
        });
    }

    // То же самое для auto_delivery_cost
    if (autoDeliveryCostInput) {
        ['input', 'change', 'blur'].forEach(function(eventType) {
            autoDeliveryCostInput.addEventListener(eventType, function() {
                console.log(`Auto delivery cost ${eventType} event:`, this.value);
                // Если auto_delivery_cost изменился, также отправляем событие
                triggerDeliveryCostChangedEvent(parseFloat(this.value) || 0);
            });
        });
    }

    // Инициализация при загрузке страницы
    toggleCalculateButton();

    // Обработчик изменения зоны доставки
    if (deliveryZoneSelect) {
        deliveryZoneSelect.addEventListener('change', function() {
            console.log('Изменена зона доставки:', this.value);
            handleDeliveryZoneChange();
        });
    }

    // Функция для проверки, включена ли доставка (теперь проверяем order_type)
    function isDeliveryEnabled() {
        const selectedDelivery = document.querySelector('input[name="delivery"]:checked');
        if (!selectedDelivery) return false;

        const selectedValue = selectedDelivery.value;
        // Проверка на delivery Beograd и delivery NoviSad (1 и 3)
        const isDelivery = (selectedValue === '1' || selectedValue === '3');

        console.log("Доставка включена:", isDelivery, "(selectedValue =", selectedValue + ")");
        return isDelivery;
    }

    // Слушаем изменение суммы заказа для пересчета промо-условий доставки
    document.addEventListener('amountChanged', function(event) {
        if (isDeliveryEnabled() && deliveryZoneSelect && deliveryZoneSelect.value) {
            console.log('Получено событие изменения суммы, пересчитываем стоимость доставки:', event.detail);
            // Не нужно запускать calculateDelivery() повторно,
            // просто проверяем промо-условия для уже выбранной зоны
            handleDeliveryZoneChange();
        }
    });

    console.log('Delivery calculation script initialization complete');
});

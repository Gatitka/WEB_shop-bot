// Создает кэши для цен (fetchedPrices) и скидок (fetchedDiscounts)
// Загружает скидки через API при загрузке страницы
// При выборе товара запрашивает цену через API, кэширует полученную цену в fetchedPrices
// Пересчитывает суммы строки и общую сумму заказа.
// Использует MutationObserver для полей суммы и скидок, автоматически пересчитывает итоговые значения при изменениях
// Суммирует стоимость всех товаров, вычитает все применимые скидки, обновляет поле финальной суммы
// Учитывает больше полей скидок - ручная + на инстаграм и пр...

///////////////////////////////////////////////   ПОЛУЧЕНИЕ ЦЕН
document.addEventListener('DOMContentLoaded', function() {

    // Функция для получения текущего домена
    function getCurrentDomain() {
        return window.location.hostname;
    }

    const currentDomain = getCurrentDomain();

    var fetchedDiscounts = {}; // Объект для хранения полученных скидок

    // Функция для выполнения запроса к эндпоинту и сохранения данных о скидке
    function fetchDiscounts() {
        let discountsApiUrl; // URL вашего API эндпоинта
        if (currentDomain === '127.0.0.1') {
                discountsApiUrl = `http://${currentDomain}:8000/api/v1/get_discounts/`;
            } else {
                discountsApiUrl = `https://${currentDomain}/api/v1/get_discounts/`;
            }

        fetch(discountsApiUrl)
            .then(response => response.json())
            .then(data => {
                fetchedDiscounts = data;
                console.log('Discounts fetched:', fetchedDiscounts);
            })
            .catch(error => {
                console.error('Error fetching discounts:', error);
            });
    }

    // Вызываем функцию для получения данных о скидке при загрузке страницы
    fetchDiscounts();

    // Создаем объект для хранения уже полученных цен
    var fetchedPrices = {};

    // Добавляем функцию для получения цен для выбранных блюд при загрузке страницы
    function fetchPricesForSelectedDishes() {
        var dishSelects = document.querySelectorAll('.field-dish select');
        dishSelects.forEach(function(select) {
            var dishId = select.value;
            console.log('dishId:', dishId);
            // Проверяем, выбрано ли блюдо перед выполнением запроса цены
            if (dishId) {
                var unitPriceField = select.closest('tr').querySelector('.field-unit_price p');
                fetchAndUpdatePrice(dishId, unitPriceField);
            }
        });
    }

    // Вызываем функцию при загрузке страницы
    fetchPricesForSelectedDishes();

    // Обработчик изменения source для пересчета цен
    document.getElementById('id_source').addEventListener('change', function() {
        document.querySelectorAll('.field-dish select').forEach(function(select) {
            if (select.value) {
                var unitPriceField = select.closest('tr').querySelector('.field-unit_price p');
                fetchAndUpdatePrice(select.value, unitPriceField);
            }
        });
    });

    // Обработчик события изменения значения выпадающего списка блюда
    document.addEventListener('change', function(event) {
        if (event.target && event.target.closest('.field-dish select')) {
            var dishId = event.target.value;
            var unitPriceField = event.target.closest('tr').querySelector('.field-unit_price p');

            // Логирование для проверки
            console.log('Change event fired for dish selection.');
            console.log('dishId:', dishId);
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

    var orderdishesTable = document.querySelector('.module table tbody');

    document.addEventListener('click', function(event) {
        // Проверяем, был ли клик по ссылке удаления
        if (event.target.classList.contains('inline-deletelink') ||
            (event.target.parentElement && event.target.parentElement.classList.contains('inline-deletelink'))) {

            console.log('Delete link clicked (delegated).');

            // Нам нужна небольшая задержка, чтобы дать Django Admin обработать удаление
            setTimeout(function() {
                console.log('Running updateOrderAmount after delete');
                updateOrderAmount();
            }, 100);
        }
    });

    // Также добавляем MutationObserver для отслеживания изменений в таблице
    var orderdishesGroup = document.getElementById('orderdishes-group');
    if (orderdishesGroup) {
        var observer = new MutationObserver(function(mutations) {
            for (var mutation of mutations) {
                if (mutation.type === 'childList') {
                    console.log('DOM mutation detected', mutation);
                    // Проверяем, было ли удаление элементов
                    if (mutation.removedNodes.length > 0) {
                        console.log('Nodes were removed', mutation.removedNodes);

                        // Проверяем, был ли удален элемент с классом dynamic-orderdishes
                        var wasOrderDishRemoved = false;
                        mutation.removedNodes.forEach(function(node) {
                            if (node.nodeType === 1 && node.classList && node.classList.contains('dynamic-orderdishes')) {
                                wasOrderDishRemoved = true;
                            }
                        });

                        if (wasOrderDishRemoved) {
                            console.log('OrderDish was removed, updating amounts');
                            updateOrderAmount();
                        }
                    }
                }
            }
        });

        // Наблюдаем за изменениями в таблице
        var tableBody = orderdishesGroup.querySelector('table tbody');
        if (tableBody) {
            observer.observe(tableBody, {
                childList: true,
                subtree: true
            });
            console.log('MutationObserver attached to', tableBody);
        }
    }

    // Функция для обновления суммы заказа
    function updateOrderAmount() {
        var unitAmountFields = document.querySelectorAll('.field-unit_amount p');
        var totalAmount = 0;
        var itemsCount = 0;

        unitAmountFields.forEach(function(field) {
            var fieldValue = parseFloat(field.textContent);
            if (!isNaN(fieldValue)) {
                totalAmount += fieldValue;

                // Подсчет количества позиций
                var quantityInput = field.closest('tr').querySelector('.field-quantity input');
                if (quantityInput) {
                    var qty = parseInt(quantityInput.value, 10);
                    if (!isNaN(qty) && qty > 0) {
                        itemsCount += qty;
                    }
                }
            }
        });

        // Обновляем все поля корректно по их конкретным селекторам

        // 1. Поле суммы заказа до скидки или итоговой суммы с учетом скидок и доставки
        // Получаем значение source для определения, какое поле обновлять

        // Обновляем соответствующее поле в зависимости от источника
        var amountField = document.querySelector('.fieldBox.field-amount .readonly');

        if (amountField) {
            amountField.textContent = totalAmount.toFixed(2);
        }

        // 2. Поле количества позиций
        var itemsQtyField = document.querySelector('.fieldBox.field-items_qty .readonly');
        if (itemsQtyField) {
            itemsQtyField.textContent = itemsCount;
        }

        // Генерируем событие об изменении суммы
        const event = new CustomEvent('amountChanged', {
            detail: { amount: totalAmount }
        });
        document.dispatchEvent(event);
    }

    // Функция выбора цены в зависимости от источника заказа
    function getSourcePrice(response, source) {
        if (['P1-1', 'P1-2'].includes(source)) {
            return response.price_p1;
        }
        if (['P2-1', 'P2-2'].includes(source)) {
            return response.price_p2;
        }
        return response.price;
    }

    // Функция для выполнения AJAX-запроса и обновления цены блюда
    function fetchAndUpdatePrice(dishId, unitPriceField) {
        const source = document.getElementById('id_source').value;

        // Формируем URL в зависимости от текущего домена
        var currentDomain = window.location.hostname;
        var fetchPriceUrl;
        if (currentDomain === '127.0.0.1') {
            fetchPriceUrl = `http://${currentDomain}:8000/api/v1/get_dish_price/?dish_id=`;
        } else {
            fetchPriceUrl = `https://${currentDomain}/api/v1/get_dish_price/?dish_id=`;
        }

        // Проверяем, была ли уже получена цена для данного блюда
        if (fetchedPrices[dishId]) {
            // Если цена уже получена, обновляем только поле с ценой
            const price = getSourcePrice(fetchedPrices[dishId], source)

            unitPriceField.innerHTML = price;
            calculateAmount(unitPriceField);
        } else {
            var xhr = new XMLHttpRequest();
            xhr.open('GET', fetchPriceUrl + dishId, true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            xhr.onreadystatechange = function() {
                if (xhr.readyState == 4 && xhr.status == 200) {
                    var response = JSON.parse(xhr.responseText);
                    // Сохраняем полученную цену
                    fetchedPrices[dishId] = response;
                    const price = getSourcePrice(response, source);
                    unitPriceField.innerHTML = price;
                    calculateAmount(unitPriceField);
                }
            };
            xhr.send();
        }
    }

///////////////////////////////////////////////   РАССЧЕТ СКИДОК

    // Создаем экземпляр MutationObserver для отслеживания изменений в элементе '.field-amount .readonly'
    // Элемент '.field-amount .readonly', за которым нужно следить
    var amountField = document.querySelector('.fieldBox.field-amount .readonly');
    var amountObserver = new MutationObserver(function(mutationsList) {
        for (var mutation of mutationsList) {
            if (mutation.type === 'childList' || mutation.type === 'subtree') {
                calculateFinalAmount();
            }
        }
    });
    // Начинаем отслеживать изменения в элементе '.field-amount .readonly'
    if (amountField) {
        amountObserver.observe(amountField, { attributes: false, childList: true, subtree: true });
    }

    // Слушаем изменения в поле суммы заказа
    document.addEventListener('amountChanged', function() {
        calculateFinalAmount();
    });


    // Создаем экземпляр MutationObserver для отслеживания изменений в элементе '.field-discount_amount .readonly'
    var discountField = document.querySelector('.field-discount_amount .readonly');
    var discountObserver = new MutationObserver(function(mutationsList) {
        for (var mutation of mutationsList) {
            if (mutation.type === 'childList' || mutation.type === 'subtree') {
                calculateFinalAmount();
            }
        }
    });
    if (discountField) {
        discountObserver.observe(discountField, { attributes: false, childList: true, subtree: true }); // Исправлено - наблюдаем за discountField
    }

    var manualDiscountField = document.getElementById('id_manual_discount');
    if (manualDiscountField) {
        manualDiscountField.addEventListener('input', function() {
            calculateFinalAmount();
        });
    }

    var discountSelect = document.getElementById('id_discount');
    if (discountSelect) {
        discountSelect.addEventListener('change', function() {
            calculateFinalAmount();
        });
    }

    // Улучшенная обработка поля стоимости доставки
    var deliveryCostInput = document.getElementById('id_delivery_cost');
    if (deliveryCostInput) {
        console.log('Found delivery cost input:', deliveryCostInput);

        // Добавляем несколько обработчиков событий для надежности
        deliveryCostInput.addEventListener('input', function() {
            console.log('Delivery cost input event fired:', this.value);
            calculateFinalAmount();
        });

        deliveryCostInput.addEventListener('change', function() {
            console.log('Delivery cost change event fired:', this.value);
            calculateFinalAmount();
        });

        // Добавляем обработчик события blur для надежности
        deliveryCostInput.addEventListener('blur', function() {
            console.log('Delivery cost blur event fired:', this.value);
            calculateFinalAmount();
        });

        // Добавляем обработчик события focus для надежности
        deliveryCostInput.addEventListener('focus', function() {
            console.log('Delivery cost focus event fired:', this.value);
            // Сохраняем текущее значение для сравнения при потере фокуса
            this.setAttribute('data-prev-value', this.value);
        });

        // Проверяем при потере фокуса, изменилось ли значение
        deliveryCostInput.addEventListener('blur', function() {
            var prevValue = this.getAttribute('data-prev-value');
            if (prevValue !== this.value) {
                console.log('Delivery cost value changed from', prevValue, 'to', this.value);
                calculateFinalAmount();
            }
        });

        // Настраиваем MutationObserver для отслеживания изменений атрибута value
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'attributes' && mutation.attributeName === 'value') {
                    console.log('Delivery cost value attribute changed:', deliveryCostInput.value);
                    calculateFinalAmount();
                }
            });
        });

        observer.observe(deliveryCostInput, { attributes: true });
    } else {
        console.warn('Delivery cost input not found!');
    }

    // Слушаем событие изменения стоимости доставки
    document.addEventListener('deliveryCostChanged', function(event) {
        console.log('Custom deliveryCostChanged event received:', event.detail);
        calculateFinalAmount();
    });

    // Функция для расчета скидок
    function calculateDiscounts() {
        // Получаем основные значения
        var deliveryCostInput = document.getElementById('id_delivery_cost');
        var amount = parseFloat(amountField.textContent) || 0;
        var deliveryCost = deliveryCostInput ? parseFloat(deliveryCostInput.value) || 0 : 0;
        var discountSelectValue = discountSelect ? discountSelect.value : '';
        var manualDiscountValue = parseFloat(manualDiscountField.value) || 0;

        // Базовая сумма для расчета скидки (с доставкой)
        var baseAmount = amount + deliveryCost;

        // Рассчитываем скидку по выбранному типу
        var discountAmount = 0;
        if (discountSelectValue && fetchedDiscounts[discountSelectValue]) {
            var discount = fetchedDiscounts[discountSelectValue];

            if (discount.discount_perc) {
                discountAmount = baseAmount * (discount.discount_perc / 100);
            } else if (discount.discount_am) {
                discountAmount = discount.discount_am;
            }
        }

        // Рассчитываем ручную скидку как процент от базовой суммы
        var manualDiscountAmount = 0;
        if (manualDiscountValue > 0) {
            manualDiscountAmount = baseAmount * (manualDiscountValue / 100);
        }

        // Общая сумма скидки
        var totalDiscountAmount = discountAmount + manualDiscountAmount;
        return totalDiscountAmount;
    }

    // Функция для расчета итоговой суммы
    function calculateFinalAmount() {
        var amount = parseFloat(amountField.textContent) || 0;
        var deliveryCost = parseFloat(deliveryCostInput.value) || 0;
        var totalDiscountAmount = calculateDiscounts() || 0;

        // Итоговая сумма = базовая сумма - скидки
        var finalAmount = (amount + deliveryCost) - totalDiscountAmount;

        // Обновляем поле final_amount_with_shipping
        var finalAmountField = document.querySelector('.fieldBox.field-final_amount_with_shipping .readonly');
        if (finalAmountField) {
            finalAmountField.textContent = finalAmount.toFixed(2);
        }
    }


    var autoDeliveryCost = document.getElementById('id_auto_delivery_cost');
    if (autoDeliveryCost) {
        autoDeliveryCost.addEventListener('change', function() {
            calculateFinalAmount();
        });
    }
})

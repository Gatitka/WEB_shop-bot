// Часть 1 из 2 (см. также calculate_change_discounts.js) бывшего calculate_change_order_fields.js.
// Отвечает за блюда заказа:
// - получение цены блюда по матрице городов (Prices[city]) через кэш или API
// - пересчет суммы строки (unit_amount) и общей суммы заказа (amount, items_qty)
// - восстановление цен после ошибки валидации формы
//
// По завершении пересчета суммы заказа дергает событие 'amountChanged' -
// на него подписан calculate_change_discounts.js, который пересчитывает итоговую сумму с учетом скидок.

document.addEventListener('DOMContentLoaded', function() {

    // Загружаем данные блюд, переданные Django
    const dishesElement = document.getElementById('dishes-data');
    const dishes = dishesElement ? JSON.parse(dishesElement.textContent) : {};
    console.log('Загруженные блюда:', dishes);

    // Кэш цен, полученных через API (для блюд, которых не было в dishes-data)
    const fetchedPrices = {};

    // Обработчик события изменения значения выпадающего списка блюда
    document.addEventListener('change', function(event) {
        if (event.target && event.target.closest('.field-dish select')) {
            var dishId = event.target.value;
            var row = event.target.closest('tr');
            var unitPriceField = row.querySelector('.field-unit_price p');

            if (!dishId || !unitPriceField) {
                return;
            }

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
            var row = field.closest('tr');
            if (!row || row.classList.contains('empty-form') || row.id.includes('__prefix__')) {
                return;
            }
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

        // 1. Поле суммы заказа
        var amountField = document.querySelector('.fieldBox.field-amount .readonly');
        if (amountField) {
            amountField.textContent = totalAmount.toFixed(2);
        }

        // 2. Поле количества позиций
        var itemsQtyField = document.querySelector('.fieldBox.field-items_qty .readonly');
        if (itemsQtyField) {
            itemsQtyField.textContent = itemsCount;
        }

        // Генерируем событие об изменении суммы - на него подписан calculate_change_discounts.js
        const event = new CustomEvent('amountChanged', {
            detail: { amount: totalAmount }
        });
        document.dispatchEvent(event);
    }

    function normalizeCity(value) {
        return (value || '').replace(/\s+/g, '').toLowerCase();
    }

    // Функция выбора цены в зависимости от источника заказа и города
    function getDishPrice(dishInfo, orderType, city) {
        const prices = dishInfo.Prices || {};

        const cityKey = Object.keys(prices).find(
            key => normalizeCity(key) === normalizeCity(city)
        );

        const cityPrices = cityKey ? prices[cityKey] : null;
        if (!cityPrices) return 0;

        if (['P1-1', 'P1-2'].includes(orderType) && cityPrices.P1 != null) {
            return cityPrices.P1;
        }

        if (['P2-1', 'P2-2'].includes(orderType) && cityPrices.P2 != null) {
            return cityPrices.P2;
        }

        return cityPrices.site ?? 0;
    }

    // Функция для выполнения AJAX-запроса и обновления цены блюда
    function fetchAndUpdatePrice(dishId, unitPriceField) {
        const orderType = document.getElementById('id_order_type').value;
        const cityField = document.querySelector('.fieldBox.field-city .readonly');
        const city = cityField ? cityField.textContent.trim() : '';

        // Формируем URL в зависимости от текущего домена
        var currentDomain = window.location.hostname;
        var fetchPriceUrl;
        if (currentDomain === '127.0.0.1') {
            fetchPriceUrl = `http://${currentDomain}:8000/api/v1/get_dish_price/?dish_id=`;
        } else {
            fetchPriceUrl = `https://${currentDomain}/api/v1/get_dish_price/?dish_id=`;
        }

        // Проверяем, была ли уже получена цена для данного блюда
        if (dishes[dishId]) {
            // Если цена уже получена, обновляем только поле с ценой
            const price = getDishPrice(dishes[dishId], orderType, city)

            unitPriceField.innerHTML = price.toFixed(2);
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
                    fetchedPrices[dishId] = response.Prices;
                    const price = getDishPrice({ Prices: response.Prices }, orderType, city);
                    unitPriceField.innerHTML = price.toFixed(2);
                    calculateAmount(unitPriceField);

                    console.log(`Цена для блюда ${dishId} получена через API: ${price}`);
                }
            };
            xhr.send();
        }
    }

    // Восстанавливаем цены блюд, если форма перезагрузилась с ошибкой валидации
    // (уже выбранные блюда есть в DOM, но их цена не подтянулась)
    function restorePricesAfterValidationError() {
        if (!window.orderAdminHasErrors) return;

        document.querySelectorAll('.field-dish select').forEach(function(select) {
            if (!select.value) return;

            const row = select.closest('tr');
            const unitPriceField = row.querySelector('.field-unit_price p');
            if (!unitPriceField) return;

            const currentPrice = parseFloat(unitPriceField.textContent || '0');
            if (!currentPrice) {
                fetchAndUpdatePrice(select.value, unitPriceField);
            }
        });
    }
    setTimeout(function() {
        restorePricesAfterValidationError();
    }, 300);

})

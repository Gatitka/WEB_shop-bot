// Создает кэши для цен и скидок
// При выборе товара получает цену из локальных данных или запрашивает через API
// Пересчитывает суммы строки и общую сумму заказа
// Использует MutationObserver для отслеживания изменений и пересчёта
// Суммирует стоимость всех товаров, обновляет поле финальной суммы

document.addEventListener('DOMContentLoaded', function() {
    // Загружаем данные категорий и блюд, переданные Django
    const dishesElement = document.getElementById('dishes-data');
    const dishes = dishesElement ? JSON.parse(dishesElement.textContent) : {};

    console.log('Загруженные блюда:', dishes);

    // Создаем объект для хранения уже полученных цен (на случай, если в dishes нет какого-то блюда)
    var fetchedPrices = {};

    // Функция для получения текущего домена
    function getCurrentDomain() {
        return window.location.hostname;
    }

    const currentDomain = getCurrentDomain();

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

    // Обработчик изменения order_type для пересчета цен
    document.getElementById('id_order_type').addEventListener('change', function() {
        // Если order_type == "P2-2", ставим без чека и оплата наличными
        // var orderTypeValue = this.value;
        // if (orderTypeValue === "P2-2") {
        //     var invoiceNo = document.getElementById('id_invoice_1');  // "Нет"
        //     invoiceNo.checked = true; // Устанавливаем "Нет"

        //     var cashPayment = document.getElementById('id_payment_type_1'); // "cash"
        //     if (cashPayment) {
        //         cashPayment.checked = true;
        //     }
        // } else {
        //     var invoiceYes = document.getElementById('id_invoice_0'); // "Да"
        //     invoiceYes.checked = true; // Если нужно, чтобы "Да" включался обратно
        // }

        // Пересчитываем цены выбранных позиций
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

            // Обновляем цену блюда
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

    // Функция для вычисления суммы orderdish после изменений (введения кол-ва/смены источника)
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

    document.addEventListener('selectedDishesChanged', function() {
		console.log('Получено событие изменения заказа');
		updateOrderAmount();
	});

    // Обработчик клика на кнопку "Добавить еще один Товар заказа"
    document.addEventListener('click', function(event) {
        if (event.target && event.target.closest('.add-row a')) {
            // Вызываем функцию для обновления суммы заказа после добавления новой строки
            updateOrderAmount();
        }
    });

    // Используем делегирование событий для обработки кликов на inline-deletelink
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
        var itemsCount = -1;

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

        // Получаем значение order_type для определения, какое поле обновлять
        var orderTypeField = document.getElementById('id_order_type');
        var orderType = orderTypeField ? orderTypeField.value : '';
        var isPartnerOrderType = ["P1-1", "P1-2", "P2-1", "P2-2", "P3-1"].includes(orderType);

        // Обновляем соответствующее поле в зависимости от источника
        var amountField = document.querySelector('.fieldBox.field-amount .readonly');
        var finalAmountField = document.querySelector('.fieldBox.field-final_amount_with_shipping .readonly');

        if (amountField) {
            amountField.textContent = totalAmount.toFixed(2);
        }
        if (isPartnerOrderType) {
            // Для партнёрских источников обновить еще final_amount
            if (finalAmountField) {
                finalAmountField.textContent = totalAmount.toFixed(2);
            }
        }

        // Поле количества позиций
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

    // Получение цены блюда в зависимости от источника заказа
    function getDishPrice(dishInfo, orderType) {
        if (['P1-1', 'P1-2'].includes(orderType)) {
            return dishInfo.Price[1]; // Цена P1
        }
        if (['P2-1', 'P2-2'].includes(orderType)) {
            return dishInfo.Price[2]; // Цена P2
        }
        return dishInfo.Price[0]; // Обычная цена
    }

    // Получение структуры цен для API-ответа из локальных данных блюда
    function getDishPriceObject(dishInfo) {
        return {
            price: dishInfo.Price[0],
            price_p1: dishInfo.Price[1],
            price_p2: dishInfo.Price[2]
        };
    }

    // Функция для получения и обновления цены блюда
    function fetchAndUpdatePrice(dishId, unitPriceField) {
        const orderType = document.getElementById('id_order_type').value;

        // Проверяем, есть ли блюдо в локальных данных
        if (dishes && dishes[dishId]) {
            // Получаем данные из локального хранилища
            const dishInfo = dishes[dishId];

            // Получаем цену в зависимости от источника
            const price = getDishPrice(dishInfo, orderType);

            // Обновляем кэш цен для возможного использования в других частях кода
            fetchedPrices[dishId] = getDishPriceObject(dishInfo);

            // Обновляем UI
            unitPriceField.innerHTML = price.toFixed(2);
            calculateAmount(unitPriceField);

            console.log(`Цена для блюда ${dishId} получена из локальных данных: ${price}`);
            return;
        }

        // Если блюда нет в локальных данных, проверяем кэш
        if (fetchedPrices[dishId]) {
            // Если цена уже получена, обновляем только поле с ценой
            const priceData = fetchedPrices[dishId];
            let price = 0;

            if (['P1-1', 'P1-2'].includes(orderType)) {
                price = priceData.price_p1;
            } else if (['P2-1', 'P2-2'].includes(orderType)) {
                price = priceData.price_p2;
            } else {
                price = priceData.price;
            }

            unitPriceField.innerHTML = price;
            calculateAmount(unitPriceField);

            console.log(`Цена для блюда ${dishId} получена из кэша: ${price}`);
            return;
        }

        // Если блюда нет ни в локальных данных, ни в кэше, запрашиваем через API
        console.log(`Запрос цены для блюда ${dishId} через API`);

        // Формируем URL в зависимости от текущего домена
        var fetchPriceUrl;
        if (currentDomain === '127.0.0.1') {
            fetchPriceUrl = `http://${currentDomain}:8000/api/v1/get_dish_price/?dish_id=`;
        } else {
            fetchPriceUrl = `https://${currentDomain}/api/v1/get_dish_price/?dish_id=`;
        }

        var xhr = new XMLHttpRequest();
        xhr.open('GET', fetchPriceUrl + dishId, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        xhr.onreadystatechange = function() {
            if (xhr.readyState == 4 && xhr.status == 200) {
                var response = JSON.parse(xhr.responseText);
                // Сохраняем полученную цену
                fetchedPrices[dishId] = response;

                let price = 0;
                if (['P1-1', 'P1-2'].includes(orderType)) {
                    price = response.price_p1;
                } else if (['P2-1', 'P2-2'].includes(orderType)) {
                    price = response.price_p2;
                } else {
                    price = response.price;
                }

                unitPriceField.innerHTML = price;
                calculateAmount(unitPriceField);

                console.log(`Цена для блюда ${dishId} получена через API: ${price}`);
            }
        };
        xhr.send();
    }
});

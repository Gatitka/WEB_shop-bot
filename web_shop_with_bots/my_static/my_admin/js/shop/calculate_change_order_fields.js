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
                calculateDiscountAmount();
                calculateDiscountedAmount();
            }
        }
    });
    // Начинаем отслеживать изменения в элементе '.field-amount .readonly'
    if (amountField) {
        amountObserver.observe(amountField, { attributes: false, childList: true, subtree: true });
    }

    // Слушаем изменения в поле суммы заказа
    document.addEventListener('amountChanged', function() {
        calculateDiscountAmount();
        calculateDiscountedAmount();
    });


    // Создаем экземпляр MutationObserver для отслеживания изменений в элементе '.field-discount_amount .readonly'
    var discountField = document.querySelector('.field-discount_amount .readonly');
    var discountObserver = new MutationObserver(function(mutationsList) {
        for (var mutation of mutationsList) {
            if (mutation.type === 'childList' || mutation.type === 'subtree') {
                calculateDiscountedAmount();
            }
        }
    });
    if (discountField) {
        discountObserver.observe(discountField, { attributes: false, childList: true, subtree: true }); // Исправлено - наблюдаем за discountField
    }


    // .field-promocode_disc_amount .readonly'

    var manualDiscountField = document.getElementById('id_manual_discount');
    if (manualDiscountField) {
        manualDiscountField.addEventListener('input', function() {
            calculateDiscountedAmount();
        });
    }

    // Обработчик изменений выбора скидки
    document.querySelectorAll('input[name="discount"]').forEach(function(el) {
        el.addEventListener('change', function() {
            calculateDiscountAmount();
            calculateDiscountedAmount();
        });
    });

    // Функция для расчета и отображения скидки
    function calculateDiscountAmount() {
        // Если это первоначальный расчет (поле уже имеет значение) и скидки еще не загружены,
        // то не пересчитываем и используем установленное значение
        if (Object.keys(fetchedDiscounts).length === 0 && discountField.textContent.trim() !== '') {
            console.log('Using existing discount value:', discountField.textContent);
            return parseFloat(discountField.textContent) || 0;
        }

        var amountField = parseFloat(document.querySelector('.fieldBox.field-amount .readonly').textContent);
        var discountField = document.querySelector('.fieldBox.field-discount_amount .readonly');
        var discountRadioButtons = document.querySelectorAll('input[name="discount"]');
        var discountAmount = 0;

        discountRadioButtons.forEach(function(radio) {
            if (radio.checked) {
                var discountId = radio.value;
                console.log('discountId:', discountId);
                console.log('fetchedDiscounts', fetchedDiscounts);
                var discount = fetchedDiscounts[discountId];

                if (discount && discount.is_active) {
                    if (discount.discount_perc !== null) {
                        discountAmount = amountField * (discount.discount_perc / 100);
                    } else if (discount.discount_am !== null) {
                        discountAmount = discount.discount_am;
                    }
                }
            }
            console.log('Amount:', amountField);
            console.log('Discount Amount:', discountAmount);

            discountField.textContent = discountAmount.toFixed(2);
            return discountAmount;
        });
    }

    // Функция для расчета суммы с учетом скидок
    function calculateDiscountedAmount() {
        // Получаем элементы с проверкой на существование
        const amountFieldElement = document.querySelector('.field-amount .readonly');
        const discountFieldElement = document.querySelector('.field-discount_amount .readonly');
        const manualDiscountElement = document.getElementById('id_manual_discount');
        const discountedAmountElement = document.querySelector('.field-discounted_amount .readonly');

        // Если нужные элементы не найдены, выходим из функции
        if (!amountFieldElement || !discountedAmountElement) {
            console.log('Необходимые DOM-элементы не найдены для расчета скидки');
            return;
        }

        // Получаем значения с проверкой на существование элементов
        const amountField = parseFloat(amountFieldElement.textContent) || 0;
        const discountAmount = discountFieldElement ? parseFloat(discountFieldElement.textContent) || 0 : 0;
        const manualDisc = manualDiscountElement ? parseFloat(manualDiscountElement.value) || 0 : 0;

        const discAmount = amountField - discountAmount - manualDisc;

        console.log('Amount:', amountField);
        console.log('Discount Amount:', discountAmount);
        console.log('Manual Discount:', manualDisc);
        console.log('Discounted Amount:', discAmount);

        // var finalDiscountedAmount = handleDiscountedAmountChange(amountField, discAmount); // Проверяем сумму с учетом скидки 25%
        document.querySelector('.field-discounted_amount .readonly').textContent = discAmount.toFixed(2);
        calculateFinalAmountWithShipping(); //
    }

    // Функция для рассчета суммы с учетом доставки
    function calculateFinalAmountWithShipping() {
        var discountedAmount = parseFloat(document.querySelector('.field-discounted_amount .readonly').textContent) || 0;
        var deliveryCost = parseFloat(document.getElementById('id_delivery_cost').value) || 0;
        var autoDeliveryCost = parseFloat(document.getElementById('id_auto_delivery_cost').value) || 0;
        var finalAmountWithShipping = discountedAmount + (deliveryCost || autoDeliveryCost);
        document.querySelector('.field-final_amount_with_shipping .readonly').textContent = finalAmountWithShipping.toFixed(2);
    }


    var autoDeliveryCost = document.getElementById('id_auto_delivery_cost');
    if (autoDeliveryCost) {
        autoDeliveryCost.addEventListener('change', function() {
            calculateFinalAmountWithShipping();
        });
    }

    var DeliveryCost = document.getElementById('id_delivery_cost');
    if (DeliveryCost) {
        DeliveryCost.addEventListener('change', function() {
            calculateFinalAmountWithShipping();
        });
    }

    // Функция для проверки суммы с учетом скидки 25%
    function handleDiscountedAmountChange(originalAmount, discAmount) {
        // Отладочный вывод для проверки вызова функции
        console.log('handleDiscountedAmountChange() вызвана');

        // Отладочный вывод для проверки переданных значений
        console.log('originalAmount:', originalAmount);
        console.log('discAmount:', discAmount);

        // Проверяем, превышает ли разница между суммами 25%
        var threshold = originalAmount * 0.25;
        var calcMessageElement = document.getElementById('id_calc_message');
        console.log('threshold:', threshold);
        if (originalAmount - discAmount > threshold) {
            // Если превышает, возвращаем максимально возможную сумму с учетом ограничения 25%
            if (calcMessageElement) {
                var maxDisc = originalAmount - threshold;
                calcMessageElement.value = 'Превышен порог макс скидки 25% / MAX сумм = ' + maxDisc;
                calcMessageElement.style.display = 'block';
            }
        }
        return discAmount;
    }







    // // Функция для рассчета скидки на самовывоз
    // function calculateTakeawayDiscount() {
    //     var deliveryType = document.querySelector('input[name="delivery"]:checked').value;
    //     var amountField = parseFloat(document.querySelector('.field-amount .readonly').textContent);
    //     var discountField = document.querySelector('.field-discount_amount .readonly');
    //     // Находим родительский элемент с классом .field-takeaway_disc_amount
    //     var takeawayDiscountField= document.getElementById('id_takeaway_disc_amount');
    //     // Если родительский элемент найден

    //     // Если поле для скидки найдено
    //     if (takeawayDiscountField) {
    //         // Если выбран самовывоз, рассчитываем скидку
    //         if (deliveryType === '2') {
    //             var discountAmount = amountField * 0.1; // 10% от суммы заказа
    //             takeawayDiscountField.value = discountAmount.toFixed(2);
    //         } else {
    //             // Если выбрана доставка, скидка на самовывоз равна 0
    //             takeawayDiscountField.value = '0.00';
    //         }
    //     }
    // }

    // // Функция для рассчета скидки наличными
    // function calculateCashDiscount() {
    //     console.log('fetchedDiscount:', fetchedDiscount);

    //     var deliveryType = document.querySelector('input[name="delivery"]:checked').value;
    //     var paymentType = document.querySelector('input[name="payment_type"]:checked').value;
    //     var amountField = parseFloat(document.querySelector('.field-amount .readonly').textContent);
    //     var languageValue = document.getElementById('id_language').value;

    //     var cashDiscount = 0; // Изначально скидка равна 0


    //     // Проверяем, есть ли данные о скидке в полученных данных и выполняются ли условия для расчета скидки
    //     if ('cash_discount' in fetchedDiscount &&
    //         fetchedDiscount['cash_discount'] !== null &&
    //         paymentType === "cash" &&
    //         languageValue === "ru" &&
    //         deliveryType === '1') {
    //         // Если есть данные о скидке и выполняются условия, рассчитываем скидку в %
    //         if ('discount_perc' in fetchedDiscount['cash_discount']) {
    //             cashDiscount = amountField * (fetchedDiscount['cash_discount']['discount_perc'] / 100);
    //         } else if ('discount_am' in fetchedDiscount['cash_discount']) {
    //             // Или используем размер скидки, если он указан
    //             cashDiscount = fetchedDiscount['cash_discount']['discount_am'];
    //         }
    //     } else {
    //         // Если условия не выполняются или данных о скидке нет, скидка равна 0
    //         cashDiscount = 0;
    //     }

    //     // Если скидка была рассчитана, устанавливаем ее в соответствующее поле
    //     if (cashDiscount !== 0) {
    //         document.querySelector('.field-cash_discount_amount .readonly').textContent = cashDiscount.toFixed(2);
    //     } else {
    //         // Если скидка не была рассчитана (равна 0), устанавливаем 0.00
    //         document.querySelector('.field-cash_discount_amount .readonly').textContent = '0.00';
    //     }
    // }
});

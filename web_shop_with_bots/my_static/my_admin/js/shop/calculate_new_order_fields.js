///////////////////////////////////////////////   ПОЛУЧЕНИЕ ЦЕН
document.addEventListener('DOMContentLoaded', function() {

    var fetchedDiscount = {}; // Объект для хранения полученных скидок
    const currentDomain = getCurrentDomain();

    // Функция для выполнения запроса к эндпоинту и сохранения данных о скидке
    function fetchDiscount() {
        let discountsApiUrl; // URL вашего API эндпоинта
        if (currentDomain === '127.0.0.1') {
            discountsApiUrl = `http://${currentDomain}:8000/api/v1/get_discounts/`;
        } else {
            discountsApiUrl = `https://${currentDomain}/api/v1/get_discounts/`;
        }

        fetch(discountsApiUrl)
            .then(response => response.json())
            .then(data => {
                fetchedDiscount = data;
                console.log('Discounts fetched:', fetchedDiscount);
            })
            .catch(error => {
                console.error('Error fetching discounts:', error);
            });
    }

    // Вызываем функцию для получения данных о скидке при загрузке страницы
    fetchDiscount();

    // Создаем объект для хранения уже полученных цен
    var fetchedPrices = {};

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

    // Функция для обновления суммы заказа
    function updateOrderAmount() {
        var unitAmountFields = document.querySelectorAll('.field-unit_amount p');
        var totalAmount = 0;
        unitAmountFields.forEach(function(field) {
            totalAmount += parseFloat(field.textContent);
        });

        var amountField = document.querySelector('.field-amount .readonly');
        amountField.textContent = totalAmount.toFixed(2);
    }

    // Функция для выполнения AJAX-запроса и обновления цены блюда
    function fetchAndUpdatePrice(dishId, unitPriceField) {
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
            unitPriceField.innerHTML = fetchedPrices[dishId];
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
                    fetchedPrices[dishId] = response.price;
                    unitPriceField.innerHTML = response.price;
                    calculateAmount(unitPriceField);
                }
            };
            xhr.send();
        }
    }

///////////////////////////////////////////////   РАССЧЕТ СКИДОК

    // Создаем экземпляр MutationObserver для отслеживания изменений в элементе '.field-amount .readonly'
    var amountObserver = new MutationObserver(function(mutationsList) {
        for (var mutation of mutationsList) {
            if (mutation.type === 'childList' || mutation.type === 'subtree') {
                // Если произошли изменения в содержимом, вызываем функции для расчета скидок
                calculateTakeawayDiscount();
                calculateCashDiscount();
                calculateDiscountedAmount();
            }
        }
    });

    // Элемент '.field-amount .readonly', за которым нужно следить
    var amountField = document.querySelector('.field-amount .readonly');

    // Начинаем отслеживать изменения в элементе '.field-amount .readonly'
    if (amountField) {
        amountObserver.observe(amountField, { attributes: false, childList: true, subtree: true });
    }


    // Слушаем изменения в поле суммы заказа и полях скидок
    var discountFields = document.querySelectorAll('.field-auth_fst_ord_disc_amount .readonly, .field-promocode_disc_amount .readonly, .field-cash_discount_amount');

    // Создаем экземпляр MutationObserver
    var observer = new MutationObserver(function(mutationsList) {
        for(var mutation of mutationsList) {
            if (mutation.type === 'childList' || mutation.type === 'subtree') {
                // Если произошли изменения в содержимом, вызываем функцию расчета скидок
                calculateDiscountedAmount();
            }
        }
    });

    // Начинаем отслеживать изменения в полях скидок
    discountFields.forEach(function(field) {
        observer.observe(field, { attributes: false, childList: true, subtree: true });
    });

    // Добавляем слежение за изменениями в элементе с id 'id_takeaway_disc_amount'
    var takeawayDiscountField = document.getElementById('id_takeaway_disc_amount');
    if (takeawayDiscountField) {
        observer.observe(takeawayDiscountField, { attributes: true, childList: true, subtree: true });
    }

    var manualDiscountField = document.getElementById('id_manual_discount');
    if (manualDiscountField) {
        manualDiscountField.addEventListener('change', function() {
            calculateDiscountedAmount();
        });
    }

    // Слушаем изменения в поле способа доставки
    var deliveryField = document.getElementById('id_delivery');
    if (deliveryField) {
        deliveryField.addEventListener('change', function() {
            calculateTakeawayDiscount();
            calculateCashDiscount(fetchedDiscount);
            calculateDiscountedAmount();
        });
    }

    // Слушаем изменения в поле способа оплаты
    var paymentField = document.getElementById('id_payment_type');
    if (paymentField) {
        paymentField.addEventListener('change', function() {
            calculateCashDiscount(fetchedDiscount);
            calculateDiscountedAmount();
        });
    }

    // Слушаем изменения в поле языка общения
    var languageField = document.getElementById('id_language');
    if (languageField) {
        languageField.addEventListener('change', function() {
            calculateCashDiscount();
            calculateDiscountedAmount();
        });
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

    // Слушаем изменения в поле '.field-discounted_amount .readonly'
    // var discountedAmountField = document.querySelector('.field-discounted_amount .readonly');
    // if (discountedAmountField) {
    //     discountedAmountField.addEventListener('DOMSubtreeModified', handleDiscountedAmountChange);
    // }

    // Функция для расчета суммы с учетом скидок
    function calculateDiscountedAmount() {
        var amountField = parseFloat(document.querySelector('.field-amount .readonly').textContent) || 0;
        var authFstOrdDisc = parseFloat(document.querySelector('.field-auth_fst_ord_disc_amount .readonly').textContent) || 0;
        var takeawayDisc = parseFloat(document.getElementById('id_takeaway_disc_amount').value) || 0;
        var promocodeDisc = parseFloat(document.querySelector('.field-promocode_disc_amount .readonly').textContent) || 0;
        var cashDisc = parseFloat(document.querySelector('.field-cash_discount_amount .readonly').textContent) || 0;
        var manualDisc = parseFloat(document.getElementById('id_manual_discount').value) || 0;
        var discAmount = amountField - authFstOrdDisc - takeawayDisc - promocodeDisc - manualDisc - cashDisc;
        console.log('discAmount:', discAmount);
        var finalDiscountedAmount = handleDiscountedAmountChange(amountField, discAmount); // Проверяем сумму с учетом скидки 25%
        document.querySelector('.field-discounted_amount .readonly').textContent = finalDiscountedAmount.toFixed(2);
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

    // Функция для рассчета скидки на самовывоз
    function calculateTakeawayDiscount() {
        var deliveryType = document.querySelector('input[name="delivery"]:checked').value;
        var amountField = parseFloat(document.querySelector('.field-amount .readonly').textContent);

        // Находим родительский элемент с классом .field-takeaway_disc_amount
        var takeawayDiscountField= document.getElementById('id_takeaway_disc_amount');
        // Если родительский элемент найден

        // Если поле для скидки найдено
        if (takeawayDiscountField) {
            // Если выбран самовывоз, рассчитываем скидку
            if (deliveryType === '2') {
                var discountAmount = amountField * 0.1; // 10% от суммы заказа
                takeawayDiscountField.value = discountAmount.toFixed(2);
            } else {
                // Если выбрана доставка, скидка на самовывоз равна 0
                takeawayDiscountField.value = '0.00';
            }
        }
    }

    // Функция для рассчета скидки наличными
    function calculateCashDiscount() {
        console.log('fetchedDiscount:', fetchedDiscount);

        var deliveryType = document.querySelector('input[name="delivery"]:checked').value;
        var paymentType = document.querySelector('input[name="payment_type"]:checked').value;
        var amountField = parseFloat(document.querySelector('.field-amount .readonly').textContent);
        var languageValue = document.getElementById('id_language').value;

        var cashDiscount = 0; // Изначально скидка равна 0


        // Проверяем, есть ли данные о скидке в полученных данных и выполняются ли условия для расчета скидки
        if ('cash_discount' in fetchedDiscount &&
            fetchedDiscount['cash_discount'] !== null &&
            paymentType === "cash" &&
            languageValue === "ru" &&
            deliveryType === '1') {
            // Если есть данные о скидке и выполняются условия, рассчитываем скидку в %
            if ('discount_perc' in fetchedDiscount['cash_discount']) {
                cashDiscount = amountField * (fetchedDiscount['cash_discount']['discount_perc'] / 100);
            } else if ('discount_am' in fetchedDiscount['cash_discount']) {
                // Или используем размер скидки, если он указан
                cashDiscount = fetchedDiscount['cash_discount']['discount_am'];
            }
        } else {
            // Если условия не выполняются или данных о скидке нет, скидка равна 0
            cashDiscount = 0;
        }

        // Если скидка была рассчитана, устанавливаем ее в соответствующее поле
        if (cashDiscount !== 0) {
            document.querySelector('.field-cash_discount_amount .readonly').textContent = cashDiscount.toFixed(2);
        } else {
            // Если скидка не была рассчитана (равна 0), устанавливаем 0.00
            document.querySelector('.field-cash_discount_amount .readonly').textContent = '0.00';
        }
    }
});

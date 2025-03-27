// Обработчик скидок для формы заказа
document.addEventListener('DOMContentLoaded', function() {
    console.log('Скрипт обработки скидок загружен');

    // Получаем основные элементы формы
    const orderTypeField = document.getElementById('id_order_type');
    const manualDiscountInput = document.getElementById('id_manual_discount');

    // Поля для сумм
    const amountField = document.querySelector('.fieldBox.field-amount .readonly');
    const deliveryCostInput = document.getElementById('id_delivery_cost');
    const finalAmountField = document.querySelector('.fieldBox.field-final_amount_with_shipping .readonly');

    // Проверяем наличие элементов
    console.log('Элементы формы:', {
        orderTypeField: !!orderTypeField,
        manualDiscountInput: !!manualDiscountInput,
        amountField: !!amountField,
        deliveryCostInput: !!deliveryCostInput,
        finalAmountField: !!finalAmountField
    });

    // Функция проверки, является ли тип партнерским
    function isPartnerOrderType(orderType) {
        return ["P1-1", "P1-2", "P2-1", "P2-2", "P3-1"].includes(orderType);
    }

    // Функция для установки ручной скидки
    function setManualDiscount(value) {
        if (manualDiscountInput) {
            manualDiscountInput.value = value;
            console.log(`Установлена ручная скидка: ${value}%`);
        }
    }

    // Функция сброса скидки на 0
    function resetDiscount() {
        setManualDiscount("0");
    }

    // Функция получения стоимости доставки
    function getDeliveryCost() {
        // Проверяем наличие value в поле id_delivery_cost
        if (deliveryCostInput && deliveryCostInput.value) {
            const cost = parseFloat(deliveryCostInput.value);
            if (!isNaN(cost)) {
                console.log('Получена стоимость доставки из поля id_delivery_cost:', cost);
                return cost;
            }
        }

        console.log('Стоимость доставки не найдена, используем 0');
        return 0;
    }

    // Функция рассчета скидок и обновления полей формы
    function calculateDiscounts() {
        const orderType = orderTypeField.value;
        console.log('Рассчет скидок для типа заказа:', orderType);

        // Если партнерский тип, скидки не применяются
        if (isPartnerOrderType(orderType)) {
            resetDiscount();

            // Приравниваем финальное поле к амаунту
            if (finalAmountField && amountField) {
                finalAmountField.textContent = amountField.textContent;
            }

            return;
        }

        // Получаем сумму заказа
        const amount = parseFloat(amountField?.textContent || "0") || 0;
        if (amount <= 0) {
            console.log('Сумма заказа = 0, скидки не рассчитываем');
            return;
        }

        // Получаем стоимость доставки
        const deliveryCost = getDeliveryCost();
        console.log('Стоимость доставки для расчета:', deliveryCost);

        // Определяем базовую сумму для расчета скидки (с доставкой)
        const baseAmount = amount + deliveryCost;
        console.log('Базовая сумма для расчета скидки:', baseAmount);

        // Получаем значение ручной скидки в процентах
        const manualDiscountPercent = manualDiscountInput ? parseFloat(manualDiscountInput.value) || 0 : 0;
        console.log('Ручная скидка (%):', manualDiscountPercent);

        // Рассчитываем финальную сумму с учетом скидки
        const finalAmount = baseAmount * (1 - manualDiscountPercent / 100);
        console.log('Финальная сумма:', finalAmount);

        // Обновляем поле итоговой суммы
        if (finalAmountField) {
            finalAmountField.textContent = finalAmount.toFixed(2);
        }
    }

    // Функция для управления скидкой в зависимости от типа заказа
    function handleOrderTypeChange() {
        const orderType = orderTypeField.value;
        console.log('Изменен тип заказа:', orderType);

        // Получаем текущее значение скидки
        const currentDiscount = manualDiscountInput ? parseFloat(manualDiscountInput.value) || 0 : 0;

        // Если тип партнерский, сбрасываем скидку
        if (isPartnerOrderType(orderType)) {
            resetDiscount();
        }
        // Если тип T (самовывоз), устанавливаем скидку 10%
        else if (orderType === 'T') {
            // Устанавливаем 10% только если поле пустое или равно 0
            if (currentDiscount === 0) {
                setManualDiscount("10");
                console.log('Установлена скидка 10% для самовывоза (поле было пустым или 0)');
            } else {
                console.log('Сохранено пользовательское значение скидки:', currentDiscount);
            }
        }
        // Для других типов (включая D - доставку) обнуляем скидку
        else {
            if (currentDiscount === 10) {  // Сбрасываем только если значение точно 10 (скидка за самовывоз)
                resetDiscount();
                console.log('Сброшена скидка для самовывоза (была 10%)');
            } else {
                // Сохраняем другие значения (пользовательские скидки или другие системные скидки)
                console.log('Сохранено значение скидки (не равное 10%):', currentDiscount);
            }
        }

        // Пересчитываем скидки
        calculateDiscounts();
    }

    // События для отслеживания изменений

    // Изменение типа заказа
    if (orderTypeField) {
        orderTypeField.addEventListener('change', handleOrderTypeChange);
    }

    // Отслеживаем изменения в полях стоимости доставки
    if (deliveryCostInput) {
        deliveryCostInput.addEventListener('change', function() {
            console.log('Изменено поле delivery_cost:', this.value);
            calculateDiscounts();
        });

        // Также слушаем событие input для мгновенной реакции при вводе
        deliveryCostInput.addEventListener('input', function() {
            console.log('Ввод в поле delivery_cost:', this.value);
            calculateDiscounts();
        });
    }

    // Отслеживаем изменения в поле ручной скидки
    if (manualDiscountInput) {
        manualDiscountInput.addEventListener('change', function() {
            console.log('Изменено поле manual_discount:', this.value);
            calculateDiscounts();
        });

        // Также слушаем событие input для мгновенной реакции при вводе
        manualDiscountInput.addEventListener('input', function() {
            console.log('Ввод в поле manual_discount:', this.value);
            calculateDiscounts();
        });
    }

    // Слушаем событие об обновлении блюд от orderdishes_management.js
    document.addEventListener('dishesUpdated', function() {
        console.log('Получено событие обновления блюд');
        calculateDiscounts();
    });

    // Добавляем обработчик для случая, когда мы знаем, что сумма изменилась
    document.addEventListener('amountChanged', function(event) {
        console.log('Получено событие изменения суммы:', event.detail);
        calculateDiscounts();
    });

    // Добавляем обработчик для случая, когда мы знаем, что стоимость доставки изменилась
    document.addEventListener('deliveryCostChanged', function(event) {
        console.log('Получено событие изменения стоимости доставки:', event.detail);
        calculateDiscounts();
    });

    // Инициализация начальных значений
    if (orderTypeField) {
        handleOrderTypeChange(); // Установка начальной скидки в зависимости от типа заказа
    }

    // Выполняем начальный расчет с небольшой задержкой, чтобы все поля успели инициализироваться
    setTimeout(function() {
        calculateDiscounts();
    }, 500);
});

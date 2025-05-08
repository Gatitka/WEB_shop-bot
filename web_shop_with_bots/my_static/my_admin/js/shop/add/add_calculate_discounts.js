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
            // Получаем значение ручной скидки в процентах
            const manualDiscountValue = getBaseAmount() * value / 100;
            console.log('Ручная скидка (DIN):', manualDiscountValue);

            manualDiscountInput.value = manualDiscountValue;
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

    // Функция получения стоимости доставки
    function getBaseAmount() {
        // Получаем сумму заказа
        const amount = parseFloat(amountField?.textContent || "0") || 0;

        // Получаем стоимость доставки
        const deliveryCost = getDeliveryCost();
        console.log('Стоимость доставки для расчета:', deliveryCost);

        // Рассчитываем финальную сумму с учетом скидки
        const baseAmount = amount + deliveryCost;
        console.log('Финальная сумма:', baseAmount);

        return baseAmount

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

        // Получаем значение ручной скидки в процентах
        const manualDiscount = manualDiscountInput ? parseFloat(manualDiscountInput.value) || 0 : 0;
        console.log('Ручная скидка (DIN):', manualDiscount);

        // Рассчитываем финальную сумму с учетом скидки
        const finalAmount = getBaseAmount() - manualDiscount;
        updateDiscountPercent()

        console.log('Финальная сумма:', finalAmount);

        // Обновляем поле итоговой суммы
        if (finalAmountField) {
            finalAmountField.textContent = finalAmount.toFixed(2);
        }
    }

    // Функция для управления скидкой в зависимости от типа заказа
    function handleDiscountChange() {
        const orderType = orderTypeField.value;
        console.log('Изменен тип заказа:', orderType);

        // Если тип T (самовывоз), устанавливаем скидку 10%
        if (orderType === 'T') {
            // Устанавливаем 10% только если поле пустое или равно 0
            setManualDiscount("10");
            console.log('Установлена скидка 10% для самовывоза ');
        }
        // Для других типов (включая D - доставку) обнуляем скидку
        else {
            resetDiscount();
            console.log('Сброшена скидка при смене типа заказа');
        }

        // Пересчитываем скидки
        calculateDiscounts();
    }

    // Добавляем отображение процента скидки
    if (manualDiscountInput) {
        // Создаем элемент для отображения процента
        var percentDisplay = document.createElement('span');
        percentDisplay.id = 'discount-percent-display';
        percentDisplay.style.marginLeft = '10px';
        percentDisplay.style.color = '#666';
        percentDisplay.style.fontStyle = 'italic';
        percentDisplay.style.display = 'inline-block';

        // Находим родительский элемент, который содержит поле ввода
        var inputContainer = manualDiscountInput.parentNode;

        // Добавляем процент сразу после поля ввода, но в той же строке
        inputContainer.insertBefore(percentDisplay, manualDiscountInput.nextSibling);

        // Функция для обновления отображения процента
        function updateDiscountPercent() {
            // Получаем сумму заказа и стоимость доставки
            var amount = parseFloat(amountField?.textContent || '0') || 0;
            var deliveryCost = parseFloat(deliveryCostInput?.value || '0') || 0;
            var baseAmount = amount + deliveryCost;

            // Получаем значение скидки
            var discountValue = parseFloat(manualDiscountInput.value || '0') || 0;

            // Рассчитываем процент если базовая сумма больше 0
            if (baseAmount > 0) {
                var percent = (discountValue / baseAmount * 100).toFixed(2);
                percentDisplay.textContent = `(${percent}%)`;
            } else {
                percentDisplay.textContent = '(0%)';
            }
        }

        // Вызываем функцию обновления процента с небольшой задержкой после загрузки страницы
        setTimeout(updateDiscountPercent, 600);
    }

    // События для отслеживания изменений

    // Изменение типа заказа
    if (orderTypeField) {
        orderTypeField.addEventListener('change', handleDiscountChange());
    }

    // Отслеживаем изменения в полях стоимости доставки
    if (deliveryCostInput) {
        deliveryCostInput.addEventListener('change', function() {
            console.log('Изменено поле delivery_cost:', this.value);
            handleDiscountChange();
        });

        // Также слушаем событие input для мгновенной реакции при вводе
        deliveryCostInput.addEventListener('input', function() {
            console.log('Ввод в поле delivery_cost:', this.value);
            handleDiscountChange();
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
        handleDiscountChange();
    });

    // Добавляем обработчик для случая, когда мы знаем, что сумма изменилась
    document.addEventListener('amountChanged', function(event) {
        console.log('Получено событие изменения суммы:', event.detail);
        handleDiscountChange();
    });

    // Добавляем обработчик для случая, когда мы знаем, что стоимость доставки изменилась
    document.addEventListener('deliveryCostChanged', function(event) {
        console.log('Получено событие изменения стоимости доставки:', event.detail);
        handleDiscountChange();
    });

    // Инициализация начальных значений
    if (orderTypeField) {
        handleDiscountChange(); // Установка начальной скидки в зависимости от типа заказа
    }

    // Выполняем начальный расчет с небольшой задержкой, чтобы все поля успели инициализироваться
    setTimeout(function() {
        calculateDiscounts();
    }, 500);
});

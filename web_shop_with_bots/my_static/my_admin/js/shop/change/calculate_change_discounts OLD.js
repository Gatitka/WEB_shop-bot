// Часть 2 из 2 (см. также calculate_change_dishes.js) бывшего calculate_change_order_fields.js.
// Отвечает за скидки и итоговую сумму заказа:
// - скидка, выбранная вручную в дропдауне id_discount
// - ручная скидка id_manual_discount (в т.ч. автоподстановка скидки за самовывоз)
// - итоговая сумма (final_amount_with_shipping) с учетом доставки и скидок
//
// Использует общие findActiveDiscountByType()/calcDiscountAmount() из discount_utils.js -
// этот файл должен быть подключен раньше данного.
//
// Слушает событие 'amountChanged', которое дергает calculate_change_dishes.js
// при пересчете суммы блюд.

document.addEventListener('DOMContentLoaded', function() {

    // Флаг, указывающий, что мы находимся в режиме редактирования, а не ввода начальных данных
    var isEditing = false;

    // Включаем режим редактирования после небольшой задержки
    setTimeout(function() {
        isEditing = true;
        console.log('Режим редактирования активирован');
    }, 500);

    // discounts (данные скидок) и константа TAKEAWAY_DISCOUNT_TYPE
    // теперь берутся из discount_utils.js (подключается раньше этого файла)

    var amountField = document.querySelector('.fieldBox.field-amount .readonly');
    var manualDiscountField = document.getElementById('id_manual_discount');
    var deliveryCostInput = document.getElementById('id_delivery_cost');
    var finalAmountField = document.querySelector('.fieldBox.field-final_amount_with_shipping .readonly');
    var discountSelect = document.getElementById('id_discount');
    // Поле "тип доставки" (id_delivery) убрано из формы изменения заказа -
    // используем единое поле "тип заказа" (id_order_type), как в форме создания.
    var orderTypeField = document.getElementById('id_order_type');

    var discountField = document.querySelector('.field-discount_amount .readonly');

    // Создаем экземпляр MutationObserver для отслеживания изменений в элементе '.field-amount .readonly'
    var amountObserver = new MutationObserver(function(mutationsList) {
        for (var mutation of mutationsList) {
            if (mutation.type === 'childList' || mutation.type === 'subtree') {
                calculateFinalAmount();
            }
        }
    });
    if (amountField) {
        amountObserver.observe(amountField, { attributes: false, childList: true, subtree: true });
    }

    // Слушаем изменения в поле суммы заказа (событие дергает calculate_change_dishes.js)
    document.addEventListener('amountChanged', function() {
        calculateFinalAmount();
    });

    // Создаем экземпляр MutationObserver для отслеживания изменений в элементе '.field-discount_amount .readonly'
    var discountObserver = new MutationObserver(function(mutationsList) {
        for (var mutation of mutationsList) {
            if (mutation.type === 'childList' || mutation.type === 'subtree') {
                calculateFinalAmount();
            }
        }
    });
    if (discountField) {
        discountObserver.observe(discountField, { attributes: false, childList: true, subtree: true });
    }

    // Настраиваем обработчики для поля ручной скидки
    if (manualDiscountField) {
        manualDiscountField.addEventListener('change', function() {
            if (isEditing) calculateFinalAmount();
        });

        manualDiscountField.addEventListener('input', function() {
            if (isEditing) calculateFinalAmount();
        });

        manualDiscountField.addEventListener('blur', function() {
            if (isEditing) calculateFinalAmount();
        });
    }

    // Обработчик изменения выбора скидки
    if (discountSelect) {
        discountSelect.addEventListener('change', function() {
            if (isEditing) calculateFinalAmount();
        });
    }

    // Обработчик изменения типа заказа (раньше слушали id_delivery, которого больше нет в форме)
    if (orderTypeField) {
        orderTypeField.addEventListener('change', function() {
            if (isEditing) {
                handleDiscountChange();
                calculateFinalAmount();
            }
        });
    }

    // Обработчики для поля стоимости доставки
    if (deliveryCostInput) {
        deliveryCostInput.addEventListener('input', function() {
            if (isEditing) calculateFinalAmount();
        });

        deliveryCostInput.addEventListener('change', function() {
            if (isEditing) calculateFinalAmount();
        });

        deliveryCostInput.addEventListener('blur', function() {
            if (isEditing) calculateFinalAmount();
        });
    }

    // Слушаем событие изменения стоимости доставки
    document.addEventListener('deliveryCostChanged', function(event) {
        console.log('Custom deliveryCostChanged event received:', event.detail);
        calculateFinalAmount();
    });

    // Функция для установки ручной скидки (значение в DIN, уже посчитанное)
    function setManualDiscount(amountDin) {
        if (manualDiscountField) {
            manualDiscountField.value = amountDin;
            console.log('Установлена ручная скидка (DIN):', amountDin);
        }
    }

    // Функция сброса скидки на 0
    function resetDiscount() {
        setManualDiscount(0);
    }

    // Функция для управления ручной скидкой в зависимости от типа заказа
    function handleDiscountChange() {
        if (!orderTypeField || !isEditing) return;

        const orderType = orderTypeField.value;
        console.log('Тип заказа:', orderType);

        // Если тип T (самовывоз), подставляем актуальную скидку из Discount(type=2)
        if (orderType === 'T') {
            const amount = parseFloat(amountField?.textContent || '0') || 0;
            const deliveryCost = parseFloat(deliveryCostInput?.value || '0') || 0;
            const baseAmount = amount + deliveryCost;

            const takeawayDiscount = findActiveDiscountByType(discounts, TAKEAWAY_DISCOUNT_TYPE);
            if (takeawayDiscount) {
                const discountAmount = calcDiscountAmount(takeawayDiscount, baseAmount);
                setManualDiscount(discountAmount);
                console.log('Установлена скидка за самовывоз:', takeawayDiscount.title, '->', discountAmount, 'DIN');
            } else {
                resetDiscount();
                console.log('Скидка за самовывоз сейчас неактивна/не настроена (Discount type=2)');
            }
        }
        // Для других типов (включая D - доставку) обнуляем ручную скидку
        else {
            resetDiscount();
            console.log('Выбран не самовывоз, сбрасываем ручную скидку');
        }
    }

    // Функция для расчета суммы скидок (дропдаун-скидка + ручная скидка)
    function calculateDiscounts() {
        if (!amountField || !finalAmountField || !isEditing) return;

        var amount = parseFloat(amountField.textContent) || 0;
        var deliveryCost = deliveryCostInput ? parseFloat(deliveryCostInput.value) || 0 : 0;
        var discountSelectValue = discountSelect ? discountSelect.value : '';
        const manualDiscountValue = parseFloat(manualDiscountField?.value || '0') || 0;

        // Базовая сумма для расчета скидки (с доставкой)
        var baseAmount = amount + deliveryCost;

        // Рассчитываем скидку по выбранному в дропдауне типу
        var discountAmount = 0;
        if (discountSelectValue && discounts[discountSelectValue]) {
            discountAmount = calcDiscountAmount(discounts[discountSelectValue], baseAmount);
        }

        // Общая сумма скидки
        // ВНИМАНИЕ: здесь скидка из дропдауна и ручная скидка складываются.
        // На бэкенде (Order.calculate_discontinued_amount) поведение другое:
        // если manual_discount не равен 0, он ПОЛНОСТЬЮ заменяет discount, а не складывается с ним.
        // Сохранил как было исторически - см. отдельное обсуждение, если нужно привести в соответствие.
        var totalDiscountAmount = discountAmount + manualDiscountValue;
        updateDiscountPercent();
        return totalDiscountAmount;
    }

    // Функция для расчета итоговой суммы
    function calculateFinalAmount() {
        if (!amountField || !finalAmountField || !isEditing) return;

        var amount = parseFloat(amountField.textContent) || 0;
        var deliveryCost = parseFloat(deliveryCostInput.value) || 0;
        var totalDiscountAmount = calculateDiscounts() || 0;

        // Итоговая сумма = базовая сумма - скидки
        var finalAmount = (amount + deliveryCost) - totalDiscountAmount;

        if (finalAmountField) {
            finalAmountField.textContent = finalAmount.toFixed(2);
        }

        console.log('Рассчитана итоговая сумма:', {
            amount: amount,
            deliveryCost: deliveryCost,
            discounts: totalDiscountAmount,
            finalAmount: finalAmount
        });
    }

    // Добавляем отображение процента скидки рядом с полем ручной скидки
    var updateDiscountPercent = function() {};
    if (manualDiscountField) {
        var percentDisplay = document.createElement('span');
        percentDisplay.id = 'discount-percent-display';
        percentDisplay.style.marginLeft = '10px';
        percentDisplay.style.color = '#666';
        percentDisplay.style.fontStyle = 'italic';
        percentDisplay.style.display = 'inline-block';

        var inputContainer = manualDiscountField.parentNode;
        inputContainer.insertBefore(percentDisplay, manualDiscountField.nextSibling);

        updateDiscountPercent = function() {
            var amount = parseFloat(amountField?.textContent || '0') || 0;
            var deliveryCost = parseFloat(deliveryCostInput?.value || '0') || 0;
            var baseAmount = amount + deliveryCost;

            var discountValue = parseFloat(manualDiscountField.value || '0') || 0;

            if (baseAmount > 0) {
                var percent = (discountValue / baseAmount * 100).toFixed(2);
                percentDisplay.textContent = `(${percent}%)`;
            } else {
                percentDisplay.textContent = '(0%)';
            }
        };

        setTimeout(updateDiscountPercent, 600);
    }

    var autoDeliveryCost = document.getElementById('id_auto_delivery_cost');
    if (autoDeliveryCost) {
        autoDeliveryCost.addEventListener('change', function() {
            calculateFinalAmount();
        });
    }

})

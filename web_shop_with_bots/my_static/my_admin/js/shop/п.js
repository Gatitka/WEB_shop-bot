// Создаем экземпляр MutationObserver для отслеживания изменений в элементе '.field-amount .readonly'
var amountObserver = new MutationObserver(function(mutationsList) {
    for (var mutation of mutationsList) {
        if (mutation.type === 'childList' || mutation.type === 'subtree') {
            calculateDiscountedAmount();
        }
    }
});

// Элемент '.field-amount .readonly', за которым нужно следить
var amountField = document.querySelector('.field-amount .readonly');

// Начинаем отслеживать изменения в элементе '.field-amount .readonly'
if (amountField) {
    amountObserver.observe(amountField, { childList: true, subtree: true });
}

// Слушаем изменения в поле суммы заказа и полях скидок
var discountFields = document.querySelectorAll('.field-discount_amount .readonly, .field-promocode_disc_amount .readonly');

// Создаем экземпляр MutationObserver
var observer = new MutationObserver(function(mutationsList) {
    for(var mutation of mutationsList) {
        if (mutation.type === 'childList' || mutation.type === 'subtree') {
            calculateDiscountedAmount();
        }
    }
});

// Начинаем отслеживать изменения в полях скидок
discountFields.forEach(function(field) {
    observer.observe(field, { childList: true, subtree: true });
});

var manualDiscountField = document.getElementById('id_manual_discount');
if (manualDiscountField) {
    manualDiscountField.addEventListener('input', function() {
        calculateDiscountedAmount();
    });
}

// Обработчик изменений выбора скидки
document.querySelectorAll('input[name="discount"]').forEach(function(el) {
    el.addEventListener('change', calculateDiscountAmount);
});

// Функция для расчета суммы с учетом скидок
function calculateDiscountedAmount() {
    var amountField = parseFloat(document.querySelector('.field-amount .readonly').textContent) || 0;
    var discountAmount = calculateDiscountAmount();
    var manualDisc = parseFloat(document.getElementById('id_manual_discount').value) || 0;
    var discAmount = discountAmount + manualDisc;
    var finalDiscountedAmount = amountField - discAmount;
    document.querySelector('.field-discounted_amount .readonly').textContent = finalDiscountedAmount.toFixed(2);
    document.querySelector('.field-discount_amount .readonly').textContent = discountAmount.toFixed(2);
    calculateFinalAmountWithShipping();
}

// Функция для расчета суммы с учетом доставки
function calculateFinalAmountWithShipping() {
    var discountedAmount = parseFloat(document.querySelector('.field-discounted_amount .readonly').textContent) || 0;
    var deliveryCost = parseFloat(document.getElementById('id_delivery_cost').value) || 0;
    var autoDeliveryCost = parseFloat(document.getElementById('id_auto_delivery_cost').value) || 0;
    var finalAmountWithShipping = discountedAmount + (deliveryCost || autoDeliveryCost);
    document.querySelector('.field-final_amount_with_shipping .readonly').textContent = finalAmountWithShipping.toFixed(2);
}

// Функция для расчета и отображения скидки
function calculateDiscountAmount() {
    var amountField = parseFloat(document.querySelector('.field-amount .readonly').textContent);
    var discountRadioButtons = document.querySelectorAll('input[name="discount"]');
    var discountAmount = 0;

    discountRadioButtons.forEach(function(radio) {
        if (radio.checked) {
            var discountId = radio.value;
            var discount = fetchedDiscount[discountId]; // fetchedDiscount должен содержать ваши скидки

            if (discount && discount.is_active) {
                if (discount.discount_perc !== null) {
                    discountAmount = amountField * (discount.discount_perc / 100);
                } else if (discount.discount_am !== null) {
                    discountAmount = discount.discount_am;
                }
            }
        }
    });

    return discountAmount;
}

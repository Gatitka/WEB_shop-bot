// Общие вспомогательные функции и данные для работы со скидками.
// Используется и в форме создания заказа (add_calculate_discounts.js),
// и в форме изменения заказа (calculate_change_discounts.js).
// Должен подключаться <script>-тегом РАНЬШЕ обоих файлов выше.
//
// Работает на верхнем уровне (не внутри DOMContentLoaded) - это безопасно,
// т.к. {{ discounts|json_script:"discounts-data" }} в шаблоне рендерится
// как обычный HTML-тег ДО этого <script src="...">, и браузер выполняет
// скрипты по мере разбора документа - элемент к этому моменту уже есть в DOM.

// Данные скидок, переданные Django (одинаковы для add- и change-формы)
const discountsElement = document.getElementById('discounts-data');
const discounts = discountsElement ? JSON.parse(discountsElement.textContent) : {};
console.log('Загруженные скидки:', discounts);

// Тип скидки "за самовывоз" -- совпадает с shop.models.Discount type=2
// (см. select_discount_api / check_takeaway в shop/models.py)
const TAKEAWAY_DISCOUNT_TYPE = 2;

// Ищет активную скидку нужного типа среди данных, загруженных с бэкенда (discounts-data)
function findActiveDiscountByType(discounts, discountType) {
    for (const id in discounts) {
        const d = discounts[id];
        if (Number(d.type) === discountType && d.is_active) {
            return d;
        }
    }
    return null;
}

// Считает сумму скидки в DIN так же, как Discount.calculate_discount() на бэкенде
function calcDiscountAmount(discount, baseAmount) {
    if (!discount) return 0;
    if (discount.discount_perc) {
        return baseAmount * parseFloat(discount.discount_perc) / 100;
    }
    if (discount.discount_am) {
        return parseFloat(discount.discount_am);
    }
    return 0;
}

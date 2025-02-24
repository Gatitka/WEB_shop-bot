// document.addEventListener("DOMContentLoaded", function () {
//     const sourceField = document.getElementById("id_source");
//     const deliveryField = document.querySelectorAll('input[name="delivery"]');
//     const discountField = document.querySelectorAll('input[name="discount"]');
//     const amountField = document.querySelector(".field-amount .readonly");
//     const finalAmountField = document.querySelector(".field-final_amount_with_shipping .readonly");

//     const discountsCache = {
//         2: { is_active: true, discount_perc: 10 }, // 10% скидка за самовывоз
//         4: { is_active: true, discount_perc: 10 }, // 10% скидка за сторис
//         5: { is_active: true, discount_perc: 15 }, // 15% скидка на день рождения
//     };

//     function getSelectedDiscount() {
//         let selectedDiscount = document.querySelector('input[name="discount"]:checked');
//         return selectedDiscount ? selectedDiscount.value : null;
//     }

//     function getAmountValue() {
//         return parseFloat(amountField.textContent) || 0;
//     }

//     function recalculateFinalAmount() {
//         let source = sourceField.value;
//         let delivery = document.querySelector('input[name="delivery"]:checked').value === "True";
//         let selectedDiscount = getSelectedDiscount();

//         let discountValue = 0;

//         if (["1", "2", "3", "4"].includes(source)) {
//             if (!delivery && selectedDiscount === "2") {
//                 discountValue = discountsCache[2]?.discount_perc || 0;
//             } else if (selectedDiscount && discountsCache[selectedDiscount]) {
//                 discountValue = discountsCache[selectedDiscount].discount_perc || 0;
//             }
//         }

//         let finalAmount = getAmountValue() * (1 - discountValue / 100);
//         finalAmountField.textContent = finalAmount.toFixed(2);
//     }

//     function setDefaultValues() {
//         sourceField.value = "3"; // Источник заказа по умолчанию = 3
//         document.querySelector('input[name="delivery"][value="False"]').checked = true; // Доставка = НЕТ
//         document.querySelector("#id_discount_1").checked = true; // Устанавливаем скидку за самовывоз
//     }

//     // Устанавливаем значения по умолчанию при загрузке
//     setDefaultValues();

//     // Слушаем изменения в источнике заказа
//     sourceField.addEventListener("change", function () {
//         let source = sourceField.value;

//         if (!["1", "2", "3", "4"].includes(source)) {
//             document.querySelector("#id_discount_0").checked = true; // Сброс скидки
//             recalculateFinalAmount();
//         }
//     });

//     // Слушаем изменения в доставке
//     deliveryField.forEach((input) => {
//         input.addEventListener("change", function () {
//             if (this.value === "True" && getSelectedDiscount() === "2") {
//                 document.querySelector("#id_discount_0").checked = true; // Сброс скидки
//             }
//             recalculateFinalAmount();
//         });
//     });

//     // Слушаем изменения в выборе скидки
//     discountField.forEach((input) => {
//         input.addEventListener("change", recalculateFinalAmount);
//     });

//     // Используем MutationObserver для отслеживания изменений суммы заказа
//     const observer = new MutationObserver(recalculateFinalAmount);
//     observer.observe(amountField, { childList: true, subtree: true, characterData: true });

//     // Первоначальный расчет при загрузке
//     recalculateFinalAmount();
// });

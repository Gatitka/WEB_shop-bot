//скрываем поля при загрузке формы, открываем только при выборе сорса не партнера
//
document.addEventListener("DOMContentLoaded", function () {
    var sourceField = document.getElementById("id_source");
    var dependentFields = document.querySelector(".form-row.field-delivery.field-discount.field-payment_type");
    var amountField = document.querySelector('.fieldBox.field-amount');
    var finalAmountField = document.querySelector('.fieldBox.field-final_amount_with_shipping');

    function toggleFields() {
        var selectedValue = sourceField.value;
        if (["1", "2", "3", "4"].includes(selectedValue)) {
            dependentFields.style.display = "block";
            amountField.style.display = "block";
            finalAmountField.style.display = "block";
        } else {
            // Для партнёрских источников
            dependentFields.style.display = "none";
            // Показываем amount и скрываем final_amount_with_shipping
            amountField.style.display = "none";
            finalAmountField.style.display = "block";
        }
    }

    // Скрываем поля при загрузке страницы
    toggleFields();

    // Добавляем обработчик изменения
    sourceField.addEventListener("change", toggleFields);
});

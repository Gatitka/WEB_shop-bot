//скрываем поля при загрузке формы, открываем только при выборе сорса не партнера
//
document.addEventListener("DOMContentLoaded", function () {
    var sourceField = document.getElementById("id_source");
    var dependentFields = document.querySelector(".form-row.field-delivery.field-discount.field-payment_type");

    function toggleFields() {
        var selectedValue = sourceField.value;
        if (["1", "2", "3", "4"].includes(selectedValue)) {
            dependentFields.style.display = "block";
        } else {
            dependentFields.style.display = "none";
        }
    }

    // Скрываем поля при загрузке страницы
    toggleFields();

    // Добавляем обработчик изменения
    sourceField.addEventListener("change", toggleFields);
});

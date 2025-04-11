//скрываем поля при загрузке формы, открываем только при выборе сорса не партнера
//доставка открывается, только если выбрано доставка ДА
document.addEventListener("DOMContentLoaded", function () {
    var orderTypeField = document.getElementById("id_order_type");
    var manualDiscountField = document.querySelector(".form-row.field-manual_discount");
    var dependentFields = document.querySelector(".form-row.field-bot_order.field-delivery_time");
    var amountField = document.querySelector('.fieldBox.field-amount');
    var finalAmountField = document.querySelector('.fieldBox.field-final_amount_with_shipping');
    const botOrderNoRadio = document.getElementById('id_bot_order_0');
    const botOrderYesRadio = document.getElementById('id_bot_order_1');
    const sourceIdField = document.querySelector('.fieldBox.field-source_id');
    var contactFieldset = null;
    var commentFieldset = null;
    var deliveryFieldset = null;

    // находим свернутые разделы контакт, коммент, доставка
    document.querySelectorAll("fieldset.module.aligned.collapse h2").forEach(function(heading) {
        var headingText = heading.textContent.trim();
        if (headingText.includes("Контактная информация")) {
            contactFieldset = heading.closest("fieldset");
        } else if (headingText.includes("Комментарий")) {
            commentFieldset = heading.closest("fieldset");
        } else if (headingText.includes("Доставка")) {
            deliveryFieldset = heading.closest("fieldset");
        }
    });

    function toggleFields() {
        var selectedValue = orderTypeField.value;
        if (["T", "D"].includes(selectedValue)) {
            manualDiscountField.style.display = "block";
            dependentFields.style.display = "block";
            amountField.style.display = "block";
            finalAmountField.style.display = "block";
            if (contactFieldset) contactFieldset.style.display = "block";
            if (commentFieldset) commentFieldset.style.display = "block";

            // Check delivery radio button
            toggleDeliveryFieldset();

        } else {
            // Для партнёрских источников
            manualDiscountField.style.display = "none";
            dependentFields.style.display = "none";
            // Показываем amount и скрываем final_amount_with_shipping
            amountField.style.display = "none";
            finalAmountField.style.display = "block";
            if (contactFieldset) contactFieldset.style.display = "none";
            if (commentFieldset) commentFieldset.style.display = "none";
            if (deliveryFieldset) deliveryFieldset.style.display = "none";
            sourceIdField.style.display = 'block';
            sourceIdField.required = true;

            // Если выбран Smoke, устанавливаем invoice в "Нет"
            if (selectedValue === 'P2-1') {
                const invoiceYesRadio = document.getElementById('id_invoice_0'); // "Да"
                const invoiceNoRadio = document.getElementById('id_invoice_1'); // "Нет"
                if (invoiceNoRadio) {
                    invoiceNoRadio.checked = true;
                }
            }
        }
    }

    function toggleDeliveryFieldset() {
        if (!deliveryFieldset) return;

        // Find which delivery option is selected
        //var deliveryYes = document.querySelector('input[name="delivery"][value="True"]');
        //var isDeliverySelected = deliveryYes && deliveryYes.checked;
        const selectedValue = orderTypeField.value;

        // Show/hide delivery fieldset based on selection
        if (selectedValue === 'D') {
            deliveryFieldset.style.display = "block";
            // Expand the fieldset if it's collapsed
            if (deliveryFieldset.classList.contains("collapsed")) {
                var collapseToggle = deliveryFieldset.querySelector(".collapse-toggle");
                if (collapseToggle) {
                    // Programmatically click the toggle to expand
                    collapseToggle.click();
                }
            }
        } else {
            deliveryFieldset.style.display = "none";
        }
    }

    // Function to handle visibility of source_id based on bot_order selection
    function updateSourceIdVisibility() {
        const selectedOrderType = orderTypeField.value;
        const isBotOrder = botOrderYesRadio && botOrderYesRadio.checked;

        if (sourceIdField) {

            if (selectedOrderType === 'D' || selectedOrderType === 'T') {
                // For internal orders, show source_id only if it's a bot order
                if (isBotOrder) {
                    sourceIdField.style.display = 'block';
                    sourceIdField.required = true;
                } else {
                    sourceIdField.style.display = 'none';
                    sourceIdField.required = false;
                    sourceIdField.value = '';
                }
            } else if (['P1-1', 'P1-2', 'P2-1', 'P2-2', 'P3-1'].includes(selectedOrderType)) {
                // Always show source_id for partner orders
                sourceIdRow.style.display = 'block';
                sourceIdField.required = true;
            } else {
                // Default case
                sourceIdRow.style.display = 'none';
                sourceIdField.required = false;
            }
        }
    }

    // Добавляем обработчик изменения
    orderTypeField.addEventListener("change", toggleFields);

    // Add event listeners for bot_order radio buttons
    if (botOrderYesRadio) botOrderYesRadio.addEventListener('change', updateSourceIdVisibility);
    if (botOrderNoRadio) botOrderNoRadio.addEventListener('change', updateSourceIdVisibility);

    // Скрываем поля при загрузке страницы
    toggleFields();
    updateSourceIdVisibility();
});

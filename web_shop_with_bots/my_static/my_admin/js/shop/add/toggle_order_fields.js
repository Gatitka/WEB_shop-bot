//скрываем поля при загрузке формы, открываем только при выборе сорса не партнера
//доставка открывается, только если выбрано доставка ДА
document.addEventListener("DOMContentLoaded", function () {
    var orderTypeField = document.getElementById("id_order_type");
    var manualDiscountField = document.querySelector(".form-row.field-manual_discount");
    // var dependentFields = document.querySelector(".form-row.field-bot_order.field-delivery_time");
    var botOrderField = document.querySelector(".fieldBox.field-bot_order");
    var deliveryTimeField = document.querySelector(".fieldBox.field-delivery_time");
    var campaignField = document.querySelector(".fieldBox.field-campaign");
    var amountField = document.querySelector('.fieldBox.field-amount');
    var finalAmountField = document.querySelector('.fieldBox.field-final_amount_with_shipping');
    const botOrderNoRadio = document.getElementById('id_bot_order_0');
    const botOrderYesRadio = document.getElementById('id_bot_order_1');
    const sourceIdField = document.querySelector('.fieldBox.field-source_id');
    const sourceIdInput = document.getElementById('id_source_id');
    var userIdField = document.querySelector(".fieldBox.field-user");
    var msngrAccountField = document.querySelector(".fieldBox.field-msngr_account");
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
        if (["T", "D", "R"].includes(selectedValue)) {
            manualDiscountField.style.display = "block";
            if (deliveryTimeField) deliveryTimeField.style.display = "block";
            if (campaignField) campaignField.style.display = "block";

            if (selectedValue === "R") {
                botOrderField.style.display = "none";
                sourceIdField.style.display = "none";

            } else {
                botOrderField.style.display = "block";
            }

            amountField.style.display = "block";
            finalAmountField.style.display = "block";
            if (contactFieldset) contactFieldset.style.display = "block";
            if (commentFieldset) commentFieldset.style.display = "block";

            // Check delivery radio button
            toggleDeliveryFieldset();

        } else {
            // Для партнёрских источников
            manualDiscountField.style.display = "none";
            botOrderField.style.display = "none";
            deliveryTimeField.style.display = "none";
            if (campaignField) campaignField.style.display = "none";
            // Показываем amount и скрываем final_amount_with_shipping
            amountField.style.display = "none";
            finalAmountField.style.display = "block";
            if (contactFieldset) contactFieldset.style.display = "none";
            if (commentFieldset) commentFieldset.style.display = "none";
            if (deliveryFieldset) deliveryFieldset.style.display = "none";
            sourceIdField.style.display = 'block';
            if (sourceIdInput) sourceIdInput.required = true;

            // Если выбран Smoke, устанавливаем invoice в "Нет"
            if (selectedValue === 'P2-1' || selectedValue === 'P2-2') {
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
                    if (sourceIdInput) sourceIdInput.required = true;
                    userIdField.style.display = 'none';
                    msngrAccountField.style.display = 'block';
                } else {
                    sourceIdField.style.display = 'none';
                    if (sourceIdInput) {
                        sourceIdInput.required = false;
                        sourceIdInput.value = '';
                    }
                    userIdField.style.display = 'block';
                    msngrAccountField.style.display = 'none';
                }
            } else if (['P1-1', 'P1-2', 'P2-1', 'P2-2', 'P3-1'].includes(selectedOrderType)) {
                // Always show source_id for partner orders
                sourceIdField.style.display = 'block';
                // if (sourceIdInput) sourceIdInput.required = true;
                if (sourceIdInput) sourceIdInput.required = false;
            } else {
                // Default case
                sourceIdField.style.display = 'none';
                if (sourceIdInput) sourceIdInput.required = false;
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

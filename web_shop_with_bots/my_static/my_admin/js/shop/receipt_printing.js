// receipt_printing.js
// на странице списка заказов организация печати чека по заказу.
// Отслеживание нажатия кнопки "Печать", отправляется запрос и получаются отформатированние данные по заказу.
// Далее ставится задача на печать через браузер.


document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token from the form
    function getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    // Add click handlers to all print buttons
    function initPrintButtons() {
        // For buttons in the changelist
        document.querySelectorAll('button.print-button').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const orderId = this.getAttribute('data-id');
                if (orderId) {
                    printReceipt(orderId);
                }
            });
        });

        // For button in the change form
        const submitRow = document.querySelector('.submit-row');
        if (submitRow) {
            const orderId = window.location.pathname.split('/').slice(-3)[0];
            const printButton = document.createElement('input');
            printButton.type = 'button';
            printButton.value = 'Печать чека';
            printButton.className = 'print-button default';
            printButton.onclick = () => printReceipt(orderId);
            submitRow.appendChild(printButton);
        }
    }

    // Print receipt
    async function printReceipt(orderId) {
        try {
            // Get receipt data from admin endpoint
            const response = await fetch(`/admin/receipt/formatted/${orderId}/`, {
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch receipt data');
            }

            const data = await response.json();

            // Print using Web Serial API
            try {
                // Request a port from the user
                const port = await navigator.serial.requestPort();
                await port.open({ baudRate: 9600 });

                const writer = port.writable.getWriter();
                const encoder = new TextEncoder();

                // Write the receipt text
                await writer.write(encoder.encode(data.receipt_text));

                writer.releaseLock();
                await port.close();

                console.log('Receipt printed successfully');
            } catch (error) {
                console.error('Printing error:', error);
                if (error.name === 'NotFoundError') {
                    alert('Принтер не найден. Пожалуйста, подключите принтер и попробуйте снова.');
                } else if (error.name === 'SecurityError') {
                    alert('Нет разрешения на доступ к принтеру. Пожалуйста, предоставьте разрешение.');
                } else {
                    alert('Ошибка при печати чека. Проверьте подключение принтера.');
                }
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Ошибка при получении данных чека');
        }
    }

    // Initialize print buttons
    initPrintButtons();
});

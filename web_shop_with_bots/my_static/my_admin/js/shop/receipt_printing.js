document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token from the form
    function getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    // Add click handlers to all print buttons
    function initPrintButtons() {
        // Кнопки в списке
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
            printButton.setAttribute('data-id', orderId);

            printButton.onclick = function() {
                printReceipt(orderId);
            };

            submitRow.appendChild(printButton);
        }
    }

    // Print receipt
    async function printReceipt(orderId) {
        try {
            console.log(`Получение данных чека для ID: ${orderId}`);

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

            // Проверяем, закодированы ли данные в base64
            if (data.is_binary) {
                // Отправляем на локальный сервер печати
                await sendToLocalPrintServer(data);
            } else {
                // Печать напрямую через Web Serial API (старый метод)
                await printDirectly(data.receipt_text);
            }

            console.log('Receipt print request sent successfully');
        } catch (error) {
            console.error('Ошибка при печати чека:', error);
            alert('Ошибка при печати чека: ' + error.message);
        }
    }

    // Печать через Web Serial API (старый метод, оставлен для совместимости)
    async function printDirectly(receiptText) {
        try {
            // Request a port from the user
            const port = await navigator.serial.requestPort();
            await port.open({ baudRate: 9600 });

            const writer = port.writable.getWriter();
            const encoder = new TextEncoder();

            // Write the receipt text
            await writer.write(encoder.encode(receiptText));

            writer.releaseLock();
            await port.close();

            console.log('Receipt printed successfully via Web Serial API');
        } catch (error) {
            console.error('Printing error:', error);
            if (error.name === 'NotFoundError') {
                alert('Принтер не найден. Пожалуйста, подключите принтер и попробуйте снова.');
            } else if (error.name === 'SecurityError') {
                alert('Нет разрешения на доступ к принтеру. Пожалуйста, предоставьте разрешение.');
            } else {
                alert('Ошибка при печати чека через Web Serial API. Используйте локальный сервер печати.');
                // Пробуем альтернативный метод - через локальный сервер
                throw new Error('Web Serial API failed, try local print server');
            }
        }
    }

    // Отправка данных на локальный сервер печати
    async function sendToLocalPrintServer(data) {
        try {
            // Адрес локального сервера печати
            const printServerUrl = 'http://localhost:5000/print';

            // Отправляем данные на локальный сервер печати
            const response = await fetch(printServerUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    receipt_data: data.receipt_text,  // Base64-кодированные данные
                    printer_settings: data.printer_settings
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`Локальный сервер печати: ${errorData.error || response.statusText}`);
            }

            const result = await response.json();
            if (result.success) {
                console.log('Receipt printed successfully via local print server');
            } else {
                throw new Error(result.error || 'Unknown error from print server');
            }
        } catch (error) {
            console.error('Error with local print server:', error);
            alert('Ошибка при печати через локальный сервер. Убедитесь, что сервер запущен и доступен.');
            throw error;
        }
    }

    // Initialize print buttons
    initPrintButtons();
});

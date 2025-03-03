document.addEventListener('DOMContentLoaded', function() {
    // Добавляем кнопку рядом с инлайн-заголовком
    const inlineGroup = document.getElementById('orderdishes-group');
    if(inlineGroup) {
        const inlineHeader = inlineGroup.querySelector('h2');
        if(inlineHeader) {
            const addButton = document.createElement('button');
            addButton.id = 'add-product-button';
            addButton.type = 'button';
            addButton.textContent = 'Добавить товар';
            addButton.style.marginLeft = '15px';
            inlineHeader.parentNode.insertBefore(addButton, inlineHeader.nextSibling);
        }

        // Добавляем модальное окно в body
        const modalHtml = `
        <div id="add-product-modal" class="modal">
            <div class="modal-content">
                <span class="close">&times;</span>
                <h2>Добавить товар</h2>
                <form id="product-form">
                    <label for="product-name">Название товара:</label>
                    <input type="text" id="product-name" name="product-name" required>
                    <button type="submit">Добавить</button>
                </form>
            </div>
        </div>`;

        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Находим элементы для всплывающего окна
        const modal = document.getElementById('add-product-modal');
        const openModalButton = document.getElementById('add-product-button');
        const closeModalButton = document.querySelector('.close');
        const productForm = document.getElementById('product-form');

        // Открываем всплывающее окно
        if (openModalButton) {
            openModalButton.addEventListener('click', function() {
                modal.style.display = 'block';
            });
        }

        // Закрываем всплывающее окно
        if (closeModalButton) {
            closeModalButton.addEventListener('click', function() {
                modal.style.display = 'none';
            });
        }

        // Закрываем окно при клике вне его области
        window.addEventListener('click', function(event) {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });

        // Обработка отправки формы
        if (productForm) {
            productForm.addEventListener('submit', function(event) {
                event.preventDefault();
                const productName = document.getElementById('product-name').value;

                // Здесь нужно добавить код для добавления товара в инлайн
                const addRowButton = inlineGroup.querySelector('.add-row a');
                if (addRowButton) {
                    addRowButton.click();

                    // Дадим время на добавление новой строки
                    setTimeout(function() {
                        // Найдем последнюю добавленную строку и заполним ее
                        const lastRow = inlineGroup.querySelector('.dynamic-orderdishes:last-child');
                        if (lastRow) {
                            // Заполним поле выбора блюда
                            const dishSelect = lastRow.querySelector('.field-dish select');
                            if (dishSelect) {
                                // Поиск опции по имени
                                for (let i = 0; i < dishSelect.options.length; i++) {
                                    if (dishSelect.options[i].text.includes(productName)) {
                                        dishSelect.selectedIndex = i;
                                        break;
                                    }
                                }

                                // Инициируем событие изменения
                                const event = new Event('change');
                                dishSelect.dispatchEvent(event);
                            }

                            // Заполним количество
                            const qtyInput = lastRow.querySelector('.field-quantity input');
                            if (qtyInput) {
                                qtyInput.value = 1;

                                // Инициируем событие изменения
                                const event = new Event('change');
                                qtyInput.dispatchEvent(event);
                            }
                        }
                    }, 500);
                }

                // Закрываем окно
                modal.style.display = 'none';
            });
        }
    }
});

/**
 * Скрипт для работы с функционалом повтора заказа
 */
document.addEventListener('DOMContentLoaded', function() {
    // Проверяем, находимся ли мы на странице добавления заказа
    if (window.location.pathname === '/admin/shop/order/add/') {
        // Получаем параметры URL
        const urlParams = new URLSearchParams(window.location.search);
        const repeatToken = urlParams.get('repeat_token');

        if (repeatToken) {
            // Показываем индикатор загрузки
            showLoading('Загрузка данных заказа...');

            // Получаем CSRF токен
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

            // Загружаем данные заказа по токену
            fetch(`/admin/shop/order/api/prepare_repeat_order/?token=${repeatToken}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => response.json())
            .then(response => {
                hideLoading();

                if (response.valid) {
                    // Заполняем форму данными
                    fillOrderForm(response.data);
                    // Показываем уведомление об успешном заполнении
                    showNotification('Данные заказа успешно загружены', 'success');
                } else {
                    // Показываем ошибку
                    showNotification(response.error || 'Произошла ошибка при загрузке данных заказа', 'error');
                }
            })
            .catch(error => {
                hideLoading();
                console.error('Ошибка при получении данных заказа:', error);
                showNotification('Произошла ошибка при загрузке данных заказа', 'error');
            });

            // Очищаем URL, чтобы при обновлении страницы не пытаться повторно загрузить данные
            if (window.history && window.history.replaceState) {
                const cleanUrl = window.location.protocol + "//" +
                                 window.location.host +
                                 window.location.pathname;
                window.history.replaceState({}, document.title, cleanUrl);
            }
        }
    }

    /**
     * Функция для заполнения формы заказа данными
     */
    function fillOrderForm(data) {
        try {
            console.log('Заполнение формы данными:', data);

            // Заполняем основные поля заказа
            fillField('id_order_type', data.order_type);
            fillField('id_city', data.city);

            // Заполняем контактные данные, если они есть
            if (data.recipient_name) fillField('id_recipient_name', data.recipient_name);
            if (data.recipient_phone) fillField('id_recipient_phone', data.recipient_phone);

            // Заполняем поля адреса и доставки, если это заказ с доставкой
            if (data.order_type === 'D') {
                if (data.recipient_address) fillField('id_recipient_address', data.recipient_address);
                if (data.coordinates) fillField('id_coordinates', data.coordinates);
                if (data.address_comment) fillField('id_address_comment', data.address_comment);

                // Имитируем событие изменения адреса для запуска расчета доставки
                if (data.recipient_address && data.coordinates) {
                    const event = new CustomEvent('coordinatesChanged', {
                        detail: { coordinates: data.coordinates }
                    });
                    document.dispatchEvent(event);
                }
            }

            // Заполняем поле способа оплаты
            if (data.payment_type) {
                fillField('id_payment_type', data.payment_type);
            }

            // Устанавливаем значение инвойса (чека)
            if (data.hasOwnProperty('invoice')) {
                const invoiceValue = data.invoice ? '1' : '0';
                const invoiceRadio = document.querySelector(`input[name="invoice"][value="${invoiceValue}"]`);
                if (invoiceRadio) {
                    invoiceRadio.checked = true;
                    // Генерируем событие изменения для радиокнопки
                    invoiceRadio.dispatchEvent(new Event('change'));
                }
            }

            // Устанавливаем комментарий
            if (data.comment) fillField('id_comment', data.comment);

            // Имитируем событие изменения типа заказа для обновления видимости полей
            if (document.getElementById('id_order_type')) {
                document.getElementById('id_order_type').dispatchEvent(new Event('change'));
            }

            // Добавляем товары в заказ после небольшой задержки
            // чтобы дать время другим скриптам инициализироваться
            setTimeout(() => {
                addDishesToOrder(data.dishes);
            }, 500);

            console.log('Форма заказа заполнена данными из повторяемого заказа');
        } catch (error) {
            console.error('Ошибка при заполнении формы заказа:', error);
            showNotification('Произошла ошибка при заполнении формы заказа', 'error');
        }
    }

    /**
     * Вспомогательная функция для заполнения полей формы
     */
    function fillField(fieldId, value) {
        const field = document.getElementById(fieldId);
        if (field) {
            field.value = value;
            // Вызываем событие изменения для запуска обработчиков
            field.dispatchEvent(new Event('change'));
        } else {
            console.warn(`Поле с ID ${fieldId} не найдено`);
        }
    }

    /**
     * Функция для добавления блюд в заказ с учетом модального окна
     */
    function addDishesToOrder(dishes) {
        if (!dishes || !dishes.length) {
            console.warn('Нет блюд для добавления в заказ');
            return;
        }

        console.log('Подготовка к добавлению блюд, всего блюд:', dishes.length);

        // Находим кнопку "Добавить блюда"
        const addButton = document.querySelector('button.add-row, a.add-row, .custom-add-button, button.custom-add-button');

        if (!addButton) {
            console.warn('Кнопка добавления блюд не найдена');
            return;
        }

        // Кликаем на кнопку, чтобы открыть модальное окно
        addButton.click();

        // Ждем открытия модального окна
        setTimeout(() => {
            // Проверяем, открылось ли модальное окно
            const modal = document.querySelector('.product-modal');

            if (!modal || window.getComputedStyle(modal).display === 'none') {
                console.warn('Модальное окно не отобразилось');
                return;
            }

            console.log('Модальное окно открыто, добавляем блюда');

            // Выбираем блюда в модальном окне
            selectDishesInModal(dishes);
        }, 500);
    }

    /**
     * Функция для выбора блюд в модальном окне
     */
    function selectDishesInModal(dishes) {
        // Находим списки категорий и блюд в модальном окне
        const categoriesList = document.querySelector('.categories-list');
        const dishesList = document.querySelector('.dishes-list');

        if (!categoriesList || !dishesList) {
            console.warn('Не найдены списки категорий или блюд в модальном окне');
            closeModal();
            return;
        }

        // Получаем список категорий
        const categories = categoriesList.querySelectorAll('.category-item');

        if (!categories.length) {
            console.warn('Список категорий пуст');
            closeModal();
            return;
        }

        // Создаем копию массива блюд, чтобы не изменять оригинал
        const dishesToSelect = [...dishes];

        // Функция для выбора блюд в текущей категории
        function selectDishesInCategory(categoryIndex = 0) {
            if (categoryIndex >= categories.length || dishesToSelect.length === 0) {
                // Все категории просмотрены или все блюда выбраны
                console.log('Завершение выбора блюд');

                // Нажимаем кнопку "Добавить блюда"
                const addDishesButton = document.querySelector('.modal-footer .add-button');
                if (addDishesButton) {
                    addDishesButton.click();
                } else {
                    console.warn('Кнопка "Добавить блюда" не найдена');
                    closeModal();
                }

                return;
            }

            // Кликаем на категорию
            categories[categoryIndex].click();

            // Ждем загрузки блюд в категории
            setTimeout(() => {
                // Получаем список блюд в текущей категории
                const dishItems = dishesList.querySelectorAll('.dish-item');

                if (!dishItems.length) {
                    console.log('В данной категории нет блюд, переходим к следующей');
                    selectDishesInCategory(categoryIndex + 1);
                    return;
                }

                // Проходим по списку блюд и ищем совпадения с нашими блюдами
                let foundDishes = false;

                for (let i = 0; i < dishItems.length; i++) {
                    const dishItem = dishItems[i];
                    const dishId = dishItem.getAttribute('data-id') || dishItem.dataset.id;

                    if (!dishId) {
                        continue;
                    }

                    // Ищем блюдо в нашем списке
                    const dishIndex = dishesToSelect.findIndex(d => d.dish_id == dishId);

                    if (dishIndex !== -1) {
                        foundDishes = true;

                        // Получаем данные о блюде
                        const dish = dishesToSelect.splice(dishIndex, 1)[0];

                        console.log(`Найдено блюдо: ${dish.name}, ID: ${dish.dish_id}, количество: ${dish.quantity}`);

                        // Устанавливаем количество блюда
                        const qtyInput = dishItem.querySelector('input[type="text"], input[type="number"]');
                        const qtyButtons = dishItem.querySelectorAll('button');

                        if (qtyInput) {
                            // Если есть поле ввода количества - используем его
                            qtyInput.value = dish.quantity;
                            qtyInput.dispatchEvent(new Event('input'));
                            qtyInput.dispatchEvent(new Event('change'));
                        } else if (qtyButtons.length) {
                            // Если есть кнопки +/- - используем их
                            let currentQty = 1; // Предполагаем, что по умолчанию количество 1

                            // Находим кнопку увеличения количества
                            let plusButton = null;
                            for (const btn of qtyButtons) {
                                if (btn.textContent.includes('+') || btn.classList.contains('plus')) {
                                    plusButton = btn;
                                    break;
                                }
                            }

                            if (plusButton) {
                                // Кликаем нужное количество раз
                                for (let j = currentQty; j < dish.quantity; j++) {
                                    plusButton.click();
                                }
                            }
                        }

                        // Выбираем блюдо (клик по блюду или кнопка "Добавить")
                        const addButton = dishItem.querySelector('button.add-dish');
                        if (addButton) {
                            addButton.click();
                        } else {
                            // Если нет кнопки, кликаем на само блюдо
                            dishItem.click();
                        }
                    }
                }

                // Переходим к следующей категории
                selectDishesInCategory(categoryIndex + 1);

            }, 300);
        }

        // Начинаем выбор блюд с первой категории
        selectDishesInCategory(0);
    }

    /**
     * Функция для закрытия модального окна
     */
    function closeModal() {
        const closeButton = document.querySelector('.product-modal .close-button, .product-modal .modal-close');
        if (closeButton) {
            closeButton.click();
        }
    }

    /**
     * Функция для отображения индикатора загрузки
     */
    function showLoading(message) {
        // Проверяем, существует ли уже индикатор загрузки
        let loadingEl = document.getElementById('repeat-order-loading');

        if (!loadingEl) {
            // Создаем элемент индикатора загрузки
            loadingEl = document.createElement('div');
            loadingEl.id = 'repeat-order-loading';
            loadingEl.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            `;

            const loaderContent = document.createElement('div');
            loaderContent.style.cssText = `
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
                text-align: center;
            `;

            const spinner = document.createElement('div');
            spinner.style.cssText = `
                border: 4px solid #f3f3f3;
                border-top: 4px solid #417690;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                animation: spin 1s linear infinite;
                margin: 0 auto 10px;
            `;

            const msgEl = document.createElement('p');
            msgEl.id = 'loading-message';
            msgEl.textContent = message || 'Загрузка...';

            // Добавляем стиль анимации
            const style = document.createElement('style');
            style.textContent = `
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(style);

            loaderContent.appendChild(spinner);
            loaderContent.appendChild(msgEl);
            loadingEl.appendChild(loaderContent);
            document.body.appendChild(loadingEl);
        } else {
            // Обновляем сообщение
            const msgEl = document.getElementById('loading-message');
            if (msgEl) msgEl.textContent = message || 'Загрузка...';

            // Показываем индикатор
            loadingEl.style.display = 'flex';
        }
    }

    /**
     * Функция для скрытия индикатора загрузки
     */
    function hideLoading() {
        const loadingEl = document.getElementById('repeat-order-loading');
        if (loadingEl) {
            loadingEl.style.display = 'none';
        }
    }

    /**
     * Функция для отображения уведомления
     */
    function showNotification(message, type = 'info') {
        // Проверяем, существует ли уже элемент уведомления
        let notificationEl = document.getElementById('repeat-order-notification');

        if (!notificationEl) {
            // Создаем элемент уведомления
            notificationEl = document.createElement('div');
            notificationEl.id = 'repeat-order-notification';
            notificationEl.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                border-radius: 4px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
                z-index: 9999;
                opacity: 0;
                transition: opacity 0.3s ease;
            `;

            document.body.appendChild(notificationEl);
        }

        // Устанавливаем цвет в зависимости от типа уведомления
        if (type === 'success') {
            notificationEl.style.backgroundColor = '#28a745';
            notificationEl.style.color = 'white';
        } else if (type === 'error') {
            notificationEl.style.backgroundColor = '#dc3545';
            notificationEl.style.color = 'white';
        } else {
            notificationEl.style.backgroundColor = '#17a2b8';
            notificationEl.style.color = 'white';
        }

        // Устанавливаем сообщение
        notificationEl.textContent = message;

        // Показываем уведомление
        notificationEl.style.opacity = '1';

        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            notificationEl.style.opacity = '0';
        }, 5000);
    }
});

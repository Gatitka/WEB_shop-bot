// Обработчик скидок для формы заказа
document.addEventListener('DOMContentLoaded', function() {
    console.log('Скрипт обработки скидок загружен');

    var fetchedDiscounts = {}; // Объект для хранения полученных скидок

    // Функция для получения текущего домена
    function getCurrentDomain() {
        return window.location.hostname;
    }

    const currentDomain = getCurrentDomain();

    // Функция для выполнения запроса к эндпоинту и сохранения данных о скидке
    function fetchDiscounts() {
        let discountsApiUrl; // URL вашего API эндпоинта
        if (currentDomain === '127.0.0.1') {
                discountsApiUrl = `http://${currentDomain}:8000/api/v1/get_discounts/`;
            } else {
                discountsApiUrl = `https://${currentDomain}/api/v1/get_discounts/`;
            }

        fetch(discountsApiUrl)
            .then(response => response.json())
            .then(data => {
                fetchedDiscounts = data;
                console.log('Discounts fetched:', fetchedDiscounts);
            })
            .catch(error => {
                console.error('Error fetching discounts:', error);
            });
    }

    // Вызываем функцию для получения данных о скидке при загрузке страницы
    fetchDiscounts();

    // Получаем основные элементы формы
    const sourceField = document.getElementById('id_source');
    const deliveryRadios = document.querySelectorAll('input[name="delivery"]');
    const discountRadios = document.querySelectorAll('input[name="discount"]');

    // Поля для сумм
    const amountField = document.querySelector('.fieldBox.field-amount .readonly');
    const finalAmountField = document.querySelector('.fieldBox.field-final_amount_with_shipping .readonly');

    // Проверяем наличие элементов
    console.log('Элементы формы:', {
        sourceField: !!sourceField,
        deliveryRadios: deliveryRadios.length,
        discountRadios: discountRadios.length,
        amountField: !!amountField,
        finalAmountField: !!finalAmountField
    });

    // Функция проверки, является ли источник партнерским
    function isPartnerSource(source) {
        return !["1", "2", "3", "4"].includes(source);
    }

    // Получить выбранную скидку
    function getSelectedDiscount() {
        let selectedDiscount = null;
        discountRadios.forEach(function(radio) {
            if (radio.checked && radio.value) {
                selectedDiscount = radio.value;
            }
        });
        return selectedDiscount;
    }

    // Получить значение доставки (true = да, false = нет)
    function getDeliveryValue() {
        let deliveryValue = false;
        deliveryRadios.forEach(function(radio) {
            if (radio.checked) {
                deliveryValue = radio.value === "true";
            }
        });
        return deliveryValue;
    }

    // Функция установки скидки
    function setDiscount(discountValue) {
        discountRadios.forEach(function(radio) {
            if (radio.value === discountValue) {
                radio.checked = true;
            }
        });
    }

    // Функция сброса скидки на "Нет скидки"
    function resetDiscount() {
        const noDiscountRadio = document.getElementById('id_discount_0');
        if (noDiscountRadio) {
            noDiscountRadio.checked = true;
        }
    }

    // Функция рассчета суммы скидки
    function calculateDiscountAmount(discountId, amount) {
        if (!discountId || !fetchedDiscounts[discountId]) {
            return 0;
        }

        const discount = fetchedDiscounts[discountId];

        if (discount.discount_perc) {
            console.log('amount:', amount);
            console.log('discount.discount_perc', discount.discount_perc);

            return amount * (discount.discount_perc / 100);
        } else if (discount.discount_am) {
            return discount.discount_am;
        }

        return 0;
    }

    // Функция рассчета скидок и обновления полей формы
    function calculateDiscounts() {
        const source = sourceField.value;
        console.log('Рассчет скидок для источника:', source);

        // Если партнерский источник, скидки не применяются
        if (isPartnerSource(source)) {
            resetDiscount();

            // Приравниваем финальное поле к амаунту
            if (finalAmountField && amountField) {
                finalAmountField.textContent = amountField.textContent;
            }

            return;
        }

        // Получаем сумму заказа
        const amount = parseFloat(amountField?.textContent || "0") || 0;
        if (amount <= 0) {
            console.log('Сумма заказа = 0, скидки не рассчитываем');
            return;
        }

        // Получаем выбранную скидку
        const selectedDiscount = getSelectedDiscount();
        console.log('Выбранная скидка:', selectedDiscount);

        // Рассчитываем сумму скидки
        const discountAmount = calculateDiscountAmount(selectedDiscount, amount);
        console.log('Сумма скидки:', discountAmount);

        // Рассчитываем сумму с учетом скидки
        const finalAmount = amount - discountAmount;

        // Обновляем поле итоговой суммы
        if (finalAmountField) {
            finalAmountField.textContent = finalAmount.toFixed(2);
        }
    }

    // Функция первоначальной настройки
    function initialSetup() {
        const source = sourceField.value;
        const isDelivery = getDeliveryValue();
        const errorReturnField = document.querySelector('.errornote');

        console.log('Начальная настройка:', {
            source: source,
            isDelivery: isDelivery
        });

        //Если источник не партнеры и доставка = нет (false), устанавливаем скидку за самовывоз
        if (!isPartnerSource(source) && !isDelivery && !errorReturnField) {
            console.log('Устанавливаем скидку за самовывоз');
            setDiscount("2"); // ID скидки за самовывоз
        } else {
            console.log('Скидка не применяется', { errorExists: !!errorReturnField });
        }
    }

    // События для отслеживания изменений

    // Изменение источника
    if (sourceField) {
        sourceField.addEventListener('change', function() {
            const newSource = this.value;
            console.log('Изменен источник заказа:', newSource);

            // Если источник партнерский, сбрасываем скидку
            if (isPartnerSource(newSource)) {
                resetDiscount();
            }
            // Если источник не партнер, и доставка = нет (false), устанавливаем скидку за самовывоз
            else if (!isPartnerSource(newSource) && !getDeliveryValue()) {
                setDiscount("2"); // ID скидки за самовывоз
            }

            // Пересчитываем скидки
            setTimeout(calculateDiscounts, 100);
        });
    }

    // Изменение доставки
    deliveryRadios.forEach(function(radio) {
        radio.addEventListener('change', function() {
            const isDelivery = this.value === "True";
            console.log('isDelivery:', isDelivery);
            const source = sourceField.value;

            console.log('Изменен тип доставки:', isDelivery ? 'Да' : 'Нет');

            // Если не партнерский источник и доставка = нет, устанавливаем скидку за самовывоз
            if (!isPartnerSource(source)) {
                if (!isDelivery) {
                    // Доставка стала НЕТ, если не выбраны другие скидки,
                    // ставим скидку на самовывоз
                    const currentDiscount = getSelectedDiscount();
                    console.log('currentDiscount:', currentDiscount);
                    if (currentDiscount !== "2" && currentDiscount !== "4" && currentDiscount !== "5") {
                        console.log('Устанавливаем скидку за самовывоз');
                        setDiscount("2"); // ID скидки за самовывоз
                    }
                } else {
                    // Доставка стала ДА, сбрасываем скидку за самовывоз, если стоит именно она
                    const currentDiscount = getSelectedDiscount();
                    console.log('currentDiscount:', currentDiscount);
                    if (currentDiscount === "2") {
                        console.log('currentDiscount === 2')
                        resetDiscount();
                        const currentDiscount = getSelectedDiscount();
                        console.log('currentDiscount:', currentDiscount);
                    }
                }
            }

            // Пересчитываем скидки
            setTimeout(calculateDiscounts, 100);
        });
    });

    // Изменение скидки
    discountRadios.forEach(function(radio) {
        radio.addEventListener('change', function() {
            console.log('Изменена скидка:', this.value);
            calculateDiscounts();
        });
    });

    // Слушаем событие об обновлении блюд от orderdishes_management.js
    document.addEventListener('dishesUpdated', function() {
        console.log('Получено событие обновления блюд');
        calculateDiscounts();
    });

    // Добавляем обработчик для случая, когда мы знаем, что сумма изменилась
    document.addEventListener('amountChanged', function() {
        console.log('Получено событие изменения суммы');
        calculateDiscounts();
    });

    // Инициализация
    fetchDiscounts();
    initialSetup();

    // Выполняем начальный расчет с небольшой задержкой, чтобы все поля успели инициализироваться
    setTimeout(calculateDiscounts, 500);

    // Добавляем событие в orderdishes_management.js
    // Этот код нужно добавить в orderdishes_management.js
    /*
    // В конце функции updateOrderAmount() добавьте:
    // Генерируем событие об изменении суммы
    const event = new CustomEvent('amountChanged', {
        detail: { amount: totalAmount }
    });
    document.dispatchEvent(event);
    */
});

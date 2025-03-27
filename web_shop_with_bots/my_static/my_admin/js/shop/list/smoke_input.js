window.onload = function() {
    console.log("Страница загружена, выполняем smoke_input.js");

    // Найдем элементы
    const smokeInput = document.getElementById("smoke-value");
    const expensesInput = document.getElementById("expenses-value");

    // Находим элемент total_cash более надежным способом
    let totalCashElement = null;
    const rows = document.querySelectorAll('table.main-table tbody tr');
    rows.forEach(function(row) {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 2 && cells[0].textContent.trim() === 'Итого Н:') {
            totalCashElement = cells[cells.length - 1];
        }
    });

    // Проверим, найдены ли элементы
    if (!smokeInput || !expensesInput || !totalCashElement) {
        console.error("Ошибка: Не найден один из элементов (smokeInput, expensesInput или totalCashElement)");
        console.log("smokeInput:", smokeInput);
        console.log("expensesInput:", expensesInput);
        console.log("totalCashElement:", totalCashElement);
        return;
    }

    // Добавляем стили для отображения минуса перед числом расходов
    const style = document.createElement('style');
    style.textContent = `
        .negative-input {
            position: relative;
            padding-left: 15px !important;
        }

        .negative-input-container {
            position: relative;
            display: inline-block;
        }

        .negative-input-container::before {
            content: "-";
            position: absolute;
            left: 5px;
            top: 50%;
            transform: translateY(-50%);
            pointer-events: none;
            z-index: 1;
        }
    `;
    document.head.appendChild(style);

    // Добавляем класс и контейнер для поля расходов
    expensesInput.classList.add('negative-input');

    // Оборачиваем поле ввода в контейнер с минусом
    const parent = expensesInput.parentNode;
    const wrapper = document.createElement('div');
    wrapper.className = 'negative-input-container';
    parent.insertBefore(wrapper, expensesInput);
    wrapper.appendChild(expensesInput);

    // Получаем начальное значение total_cash из содержимого HTML
    const initialTotalCash = parseFloat(totalCashElement.textContent) || 0;
    console.log("Начальное значение total_cash:", initialTotalCash);

    // Константы для работы с хранилищем
    const STORAGE_KEY = 'report_values';

    // Функция для получения текущей даты в формате YYYY-MM-DD
    function getCurrentDate() {
        const now = new Date();
        return now.getFullYear() + '-' +
               String(now.getMonth() + 1).padStart(2, '0') + '-' +
               String(now.getDate()).padStart(2, '0');
    }

    // Функция для сохранения текущих значений в локальное хранилище
    function saveValues() {
        const data = {
            date: getCurrentDate(),
            smoke: smokeInput.value,
            expenses: expensesInput.value
        };

        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        console.log('Данные сохранены:', data);
    }

    // Функция для загрузки значений из локального хранилища
    function loadValues() {
        const savedDataJson = localStorage.getItem(STORAGE_KEY);

        if (savedDataJson) {
            try {
                const savedData = JSON.parse(savedDataJson);
                const today = getCurrentDate();

                // Проверяем, что данные за сегодняшний день
                if (savedData.date === today) {
                    console.log('Загружены сохраненные данные:', savedData);

                    // Установка значений в поля ввода
                    smokeInput.value = savedData.smoke || 0;
                    expensesInput.value = savedData.expenses || 0;

                    // Обновляем итоговую сумму
                    updateTotalCash();

                    return true;
                } else {
                    console.log('Найдены данные за другой день, сбрасываем:', savedData.date);
                    localStorage.removeItem(STORAGE_KEY);
                }
            } catch (e) {
                console.error('Ошибка при разборе сохраненных данных:', e);
                localStorage.removeItem(STORAGE_KEY);
            }
        }

        return false;
    }

    // Функция обновления total_cash при изменении инпутов
    function updateTotalCash() {
        const smokeValue = parseFloat(smokeInput.value) || 0;
        const expensesValue = parseFloat(expensesInput.value) || 0;

        // Добавляем smoke и вычитаем expenses
        const newTotalCash = initialTotalCash + smokeValue - expensesValue;

        console.log(`Обновляем сумму: ${initialTotalCash} + ${smokeValue} - ${expensesValue} = ${newTotalCash}`);
        totalCashElement.textContent = newTotalCash.toFixed(2);

        // Сохраняем данные при каждом изменении
        saveValues();
    }

    // Функция для очистки значения при фокусе, если оно равно 0
    function clearZeroOnFocus(event) {
        if (event.target.value === "0" || event.target.value === "0.00") {
            event.target.value = "";
        }
    }

    // Функция для возврата значения 0, если поле пустое при потере фокуса
    function restoreZeroOnBlur(event) {
        if (event.target.value === "") {
            event.target.value = "0";
            // Обновляем сумму, чтобы учесть изменение
            updateTotalCash();
        } else {
            // Если значение не пустое, но изменилось, сохраняем
            saveValues();
        }
    }

    // Вешаем обработчики событий на оба input для изменения значения
    smokeInput.addEventListener("input", updateTotalCash);
    expensesInput.addEventListener("input", updateTotalCash);

    // Вешаем обработчики для очистки и восстановления нулей
    smokeInput.addEventListener("focus", clearZeroOnFocus);
    expensesInput.addEventListener("focus", clearZeroOnFocus);
    smokeInput.addEventListener("blur", restoreZeroOnBlur);
    expensesInput.addEventListener("blur", restoreZeroOnBlur);

    // При инициализации пытаемся загрузить сохраненные данные
    if (!loadValues()) {
        // Если данных нет или они устарели, устанавливаем начальное значение
        totalCashElement.textContent = initialTotalCash.toFixed(2);
    }
};

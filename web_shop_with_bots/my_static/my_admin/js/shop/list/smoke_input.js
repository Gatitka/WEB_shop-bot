window.onload = function() {
    console.log("Страница загружена, выполняем smoke_input.js");

    // Найдем элементы
    const smokeInput = document.getElementById("smoke-value");
    const totalCashElement = document.querySelector(".total-sum-row .numeric");

    // Проверим, найдены ли элементы
    if (!smokeInput || !totalCashElement) {
        console.error("Ошибка: Не найден один из элементов (smokeInput или totalCashElement)");
        return;
    }

    // Получаем начальное значение total_cash из содержимого HTML
    const initialTotalCash = parseFloat(totalCashElement.textContent) || 0;
    console.log("Начальное значение total_cash:", initialTotalCash);

    // Функция обновления total_cash при изменении smokeInput
    function updateTotalCash() {
        const smokeValue = parseFloat(smokeInput.value) || 0;
        const newTotalCash = initialTotalCash + smokeValue;

        console.log(`Обновляем сумму: ${initialTotalCash} + ${smokeValue} = ${newTotalCash}`);
        totalCashElement.textContent = newTotalCash.toFixed(2);
    }

    // Вешаем обработчик событий на input
    smokeInput.addEventListener("input", updateTotalCash);

    // Устанавливаем начальное значение
    totalCashElement.textContent = initialTotalCash.toFixed(2);
};

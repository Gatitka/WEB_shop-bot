document.addEventListener('DOMContentLoaded', function() {
    // Получаем данные категорий
    const categoriesElement = document.getElementById('categories-data');
    const categories = categoriesElement ? JSON.parse(categoriesElement.textContent) : {};

    // Получаем данные блюд
    const dishesElement = document.getElementById('dishes-data');
    const dishes = dishesElement ? JSON.parse(dishesElement.textContent) : {};

    console.log('Загруженные категории:', categories);
    console.log('Загруженные блюда:', dishes);
});

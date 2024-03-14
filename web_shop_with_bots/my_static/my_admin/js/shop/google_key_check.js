// js/address_autocomplete.js

document.addEventListener('DOMContentLoaded', () => {
    // Проверяем, был ли передан ключ Google API
    if (typeof window.GOOGLE_API_KEY !== 'undefined') {
        // Если ключ определен, используем его для чего-то
        console.log('Ключ Google API передан:', window.GOOGLE_API_KEY);
    } else {
        // В противном случае, выдаем сообщение об ошибке
        console.error('Ключ Google API не был передан !!!');
    }

    // Ваш остальной код для работы с ключом Google API здесь
});

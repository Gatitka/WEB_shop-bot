// Функция для получения CSRF-токена из куки
function getCSRFToken() {
    const csrfCookie = document.cookie.split(';').find(cookie => cookie.trim().startsWith('csrftoken='));
    if (csrfCookie) {
        return csrfCookie.split('=')[1];
    }
    return null;
}

// Функция для получения текущего домена
function getCurrentDomain() {
    return window.location.hostname;
}

document.addEventListener('DOMContentLoaded', () => {
    const addressInput = document.getElementById('id_recipient_address');
    const coordinatesInput = document.getElementById('id_coordinates'); // Добавлено определение поля с координатами
    const citySelect = document.getElementById('id_city'); // Поле выбора города
    const options = {
        componentRestrictions: { country: 'rs' },
        strictBounds: true,
        types: ['address']
    };

    // Функция для отображения координат в help_text под полем адреса
    function displayCoordinatesInHelpText(coordinates) {
        // Ищем или создаем help text под полем адреса
        let helpText = addressInput.parentNode.querySelector('.help');
        if (!helpText) {
            helpText = document.createElement('div');
            helpText.className = 'help';
            addressInput.parentNode.appendChild(helpText);
        }

        // Устанавливаем текст с координатами
        if (coordinates) {
            helpText.textContent = `коорд: ${coordinates}`;
            helpText.style.display = 'block';
        } else {
            helpText.style.display = 'none';
        }
    }

    if (addressInput) {
        const csrfToken = getCSRFToken();
        const currentDomain = getCurrentDomain(); // Получаем текущий домен

        // Определяем URL для запроса Google API Key в зависимости от текущего домена
        let googleApiKeyUrl;
        if (currentDomain === '127.0.0.1') {
            googleApiKeyUrl = `http://${currentDomain}:8000/api/v1/get_google_api_key/`;
        } else {
            googleApiKeyUrl = `https://${currentDomain}/api/v1/get_google_api_key/`;
        }

        console.log('Sending request to fetch Google API key...');
        fetch(googleApiKeyUrl, { // Используем определенный URL
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch Google API key');
            }
            console.log('Google API key fetched successfully.');
            return response.json();
        })
        .then(data => {
            const googleApiKey = data.GOOGLE_API_KEY;
            const googleMapsScript = document.createElement('script');
            googleMapsScript.src = `https://maps.googleapis.com/maps/api/js?key=${googleApiKey}&libraries=places`;
            googleMapsScript.defer = true;
            googleMapsScript.async = true; // Добавляем async атрибут
            googleMapsScript.onload = () => {
                console.log('Google Maps Places API script loaded successfully.');
                const autoComplete = new google.maps.places.Autocomplete(addressInput, options);
                autoComplete.addListener('place_changed', () => {
                    const place = autoComplete.getPlace(); // Получение объекта местоположения
                    if (!place.geometry || !place.geometry.location) {
                        console.error('Location not found');
                        coordinatesInput.value = ''; // Установка пустой строки для очистки поля
                        return;
                    }
                    const latitude = place.geometry.location.lat(); // Получение широты
                    const longitude = place.geometry.location.lng(); // Получение долготы
                    const coordinates = `${latitude}, ${longitude}`;
                    // Вставка координат в поле coordinates
                    coordinatesInput.value = coordinates;

                    // Отображаем координаты в help_text
                    displayCoordinatesInHelpText(coordinates);

                    // Добавьте эти отладочные выводы
                    console.log("Координаты получены и установлены:", coordinates);
                    console.log("Генерация события coordinatesChanged");

                    // Генерируем событие изменения координат для других скриптов
                    const event = new CustomEvent('coordinatesChanged', {
                        detail: { coordinates: coordinates }
                    });
                    document.dispatchEvent(event);
                    console.log("Событие coordinatesChanged отправлено");
                });
            };
            document.head.appendChild(googleMapsScript);

            // Добавляем обработчик события input для поля адреса
            addressInput.addEventListener('input', () => {
                if (!addressInput.value) {
                    coordinatesInput.value = ''; // Установка пустой строки для очистки поля
                    displayCoordinatesInHelpText('нет координат'); // Очищаем help text

                    // Сбрасываем зону доставки на значение по умолчанию
                    const deliveryZoneSelect = document.getElementById('id_delivery_zone');
                    if (deliveryZoneSelect) {
                        deliveryZoneSelect.value = '';

                        // Сбрасываем стоимость доставки на 0
                        const deliveryCostInput = document.getElementById('id_delivery_cost');
                        if (deliveryCostInput) {
                            deliveryCostInput.value = '0';

                            // Генерируем событие изменения для deliveryCostInput
                            deliveryCostInput.dispatchEvent(new Event('change'));
                        }

                        // Генерируем событие изменения для запуска связанных обработчиков
                        deliveryZoneSelect.dispatchEvent(new Event('change'));
                    }

                    // Генерируем событие изменения координат для других скриптов
                    const event = new CustomEvent('coordinatesChanged', {
                        detail: { coordinates: '' }
                    });
                    document.dispatchEvent(event);
                }
            });
        })
        .catch(error => console.error('Error fetching Google API key:', error));
    }
});

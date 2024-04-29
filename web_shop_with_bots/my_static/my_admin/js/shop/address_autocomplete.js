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
    const options = {
        componentRestrictions: { country: 'rs' },
        strictBounds: true,
        types: ['address']
    };

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
                });
            };
            document.head.appendChild(googleMapsScript);

            // Добавляем обработчик события input для поля адреса
            addressInput.addEventListener('input', () => {
                if (!addressInput.value) {
                    coordinatesInput.value = ''; // Установка пустой строки для очистки поля
                }
            });
        })
        .catch(error => console.error('Error fetching Google API key:', error));
    }
});

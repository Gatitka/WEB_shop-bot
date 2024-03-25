document.addEventListener('DOMContentLoaded', () => {
    const userField = document.getElementById('id_user');
    const recipientNameField = document.getElementById('id_recipient_name');
    const recipientPhoneField = document.getElementById('id_recipient_phone');
    const myRecipientAddressField = document.getElementById('id_my_recipient_address');
    const addressCoordinatesField = document.getElementById('id_address_coordinates');

    function updateUserFields() {
        const userId = userField.value;
        if (userId) {
            fetch(`/api/v1/get_user_data/?user_id=${userId}`)
                .then(response => response.json())
                .then(data => {
                    recipientNameField.value = data.recipient_name || '';
                    recipientPhoneField.value = data.recipient_phone || '';

                    // Обновляем список адресов
                    const addresses = data.my_addresses || [];
                    updateAddressChoices(addresses);
                })
                .catch(error => {
                    console.error('Ошибка при получении данных пользователя:', error);
                    // Обработка ошибки
                });
        }
    }

    function updateAddressChoices(addresses) {
        // Очищаем старые варианты адресов
        myRecipientAddressField.innerHTML = '';

        // Создаем вариант "None"
        const noneOption = document.createElement('option');
        noneOption.value = ''; // Устанавливаем пустое значение
        noneOption.textContent = 'None'; // Устанавливаем текст
        myRecipientAddressField.appendChild(noneOption);

        // Создаем новые варианты адресов и добавляем их в поле выбора
        addresses.forEach(address => {
            const option = document.createElement('option');
            // Удаляем слово "Адрес" из адреса перед установкой его как значения и текста опции
            const addressWithoutPrefix = address.address.replace('Адрес ', '');
            option.value = addressWithoutPrefix; // Устанавливаем значение опции
            option.textContent = addressWithoutPrefix; // Устанавливаем текст опции
            myRecipientAddressField.appendChild(option);

            // Добавляем координаты адреса в скрытое поле формы
            const coordinates = JSON.stringify({
                lat: address.lat,
                lon: address.lon
            });
            option.setAttribute('data-coordinates', coordinates);
        });
    }


    function handleAddressSelection() {
        const selectedOption = myRecipientAddressField.options[myRecipientAddressField.selectedIndex];
        const coordinates = selectedOption.getAttribute('data-coordinates');
        if (coordinates) {
            // Устанавливаем значение скрытого поля с координатами
            addressCoordinatesField.value = coordinates;

            // Добавляем координаты в скрытое поле формы
            const coordinatesInput = document.getElementById('id_address_coordinates');
            coordinatesInput.value = coordinates;
        }
    }

    if (userField) {
        // Добавляем обработчик события change для поля userField
        userField.addEventListener('change', updateUserFields);

        // Добавляем обработчик события change для ссылки, открывающей окно выбора пользователя
        const lookupLink = document.getElementById('lookup_id_user');
        if (lookupLink) {
            lookupLink.addEventListener('click', updateUserFields);
        }

        // Добавляем обработчик события change для поля выбора адреса
        myRecipientAddressField.addEventListener('change', handleAddressSelection);

        // Вызываем функцию для обновления полей при загрузке страницы
        updateUserFields();
    }
});

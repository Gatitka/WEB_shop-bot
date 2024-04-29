document.addEventListener('DOMContentLoaded', () => {
    const userField = document.getElementById('id_user');
    const recipientNameField = document.getElementById('id_recipient_name');
    const recipientPhoneField = document.getElementById('id_recipient_phone');
    const myDeliveryAddressField = document.getElementById('id_my_delivery_address');
    const addressCoordinatesField = document.getElementById('id_address_coordinates');


    function updateUserFields() {
        const userId = userField.value;
        if (userId) {
            fetch(`/api/v1/get_user_data/?user_id=${userId}`)
                .then(response => response.json())
                .then(data => {
                    recipientNameField.value = data.recipient_name || '';
                    recipientPhoneField.value = data.recipient_phone || '';
                    // Устанавливаем язык
                    const languageField = document.getElementById('id_language');
                    if (data.language) {
                        // Находим опцию с соответствующим значением языка и устанавливаем ее выбранной
                        const languageOption = languageField.querySelector(`option[value="${data.language}"]`);
                        if (languageOption) {
                            languageOption.selected = true;
                        }
                    }
                    // Обновляем список адресов
                    const myAddresses = data.my_addresses || [];
                    updateAddressChoices(myAddresses);
                })
                .catch(error => {
                    console.error('Ошибка при получении данных пользователя:', error);
                    // Обработка ошибки
                });
        }
    }

    function updateAddressChoices(myAddresses) {
        // Очищаем старые варианты адресов
        myDeliveryAddressField.innerHTML = '';

        // Создаем вариант "None"
        const noneOption = document.createElement('option');
        noneOption.value = ''; // Устанавливаем пустое значение
        noneOption.textContent = 'None'; // Устанавливаем текст
        myDeliveryAddressField.appendChild(noneOption);

        // Создаем новые варианты адресов и добавляем их в поле выбора
        myAddresses.forEach(address => {
            const option = document.createElement('option');
            const fullAddress = `${address.address}, ${address.address_comment}`;
            option.value = address.id; // Устанавливаем значение опции как id адреса
            option.textContent = fullAddress; // Устанавливаем текст опции как объединенную строку адреса и комментария
            myDeliveryAddressField.appendChild(option);

            // Добавляем координаты адреса в скрытое поле формы
            option.setAttribute('data-coordinates', address.coordinates);
            option.setAttribute('data-address_comment', address.address_comment);
        });

        // Обработчик события change для поля выбора адреса
        myDeliveryAddressField.addEventListener('change', handleAddressSelection);

        // Функция для обработки выбора адреса
        function handleAddressSelection() {
            console.log('Delivery address selected.');
            const selectedOption = myDeliveryAddressField.options[myDeliveryAddressField.selectedIndex];

            const coordinates = selectedOption.getAttribute('data-coordinates');
            if (coordinates) {
                // Устанавливаем значение скрытого поля с координатами
                const coordinatesInput = document.querySelector('#id_coordinates');
                coordinatesInput.value = coordinates;
            }

            const addressComment = selectedOption.getAttribute('data-address_comment');
            if (addressComment) {
                // Устанавливаем значение скрытого поля с данными адреса
                const addressCommentInput = document.querySelector('#id_address_comment');
                addressCommentInput.value = addressComment;
            }
        }
    }



    function handleAddressSelection() {
        console.log('Delivery address selected.');
        const selectedOption = myDeliveryAddressField.options[myDeliveryAddressField.selectedIndex];
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
        userField.addEventListener('keyup', function() {
            console.log('User field changed.');
            updateUserFields();
        });

        // // Добавляем обработчик события change для ссылки, открывающей окно выбора пользователя
        // const lookupLink = document.getElementById('lookup_id_user');
        // if (lookupLink) {
        //     lookupLink.addEventListener('click', updateUserFields);
        // }

        // Добавляем обработчик события change для поля выбора адреса
        myDeliveryAddressField.addEventListener('change', handleAddressSelection);

        // Вызываем функцию для обновления полей при загрузке страницы
        updateUserFields();
    }
});

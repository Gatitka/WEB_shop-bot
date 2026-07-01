document.addEventListener('DOMContentLoaded', () => {
    const userField = document.getElementById('id_user');
    const recipientNameField = document.getElementById('id_recipient_name');
    const recipientPhoneField = document.getElementById('id_recipient_phone');

    function updateUserFields() {
        const userId = userField.value;
        if (userId) {
            fetch(`/api/v1/get_user_data/?user_id=${userId}`)
                .then(response => response.json())
                .then(data => {
                    recipientNameField.value = recipientNameField.value || data.recipient_name || '';
                    recipientPhoneField.value = recipientPhoneField.value || data.recipient_phone || '';
                    // Устанавливаем язык
                    const languageField = document.getElementById('id_language');
                    const selectedLanguage = languageField.value;
                    if (data.language && selectedLanguage == 'sr-latn') {
                        // Находим опцию с соответствующим значением языка и устанавливаем ее выбранной
                        const languageOption = languageField.querySelector(`option[value="${data.language}"]`);
                        if (languageOption) {
                            languageOption.selected = true;
                        }
                    }
                })
                .catch(error => {
                    console.error('Ошибка при получении данных пользователя:', error);
                    // Обработка ошибки
                });
        }
    }

    if (userField) {
        userField.addEventListener('keyup', function() {
            console.log('User field changed.');
            updateUserFields();
        });
    }
});

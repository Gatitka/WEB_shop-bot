document.addEventListener('DOMContentLoaded', function () {

    // Обработка цвета select
    const statusSelects = document.querySelectorAll('td.field-status select');
    statusSelects.forEach(select => {
        // Установка начального цвета
        select.setAttribute('data-selected', select.value);

        // Обновление цвета при изменении
        select.addEventListener('change', function() {
            this.setAttribute('data-selected', this.value);
        });
    });

});

$(document).ready(function() {
    // Функция для обновления поля unit_price при изменении выбранного блюда
    $('#id_cartdishes-__prefix__-dish').on('change', function() {
        var dishName = $(this).find(':selected').attr('title');  // Получаем название выбранного блюда
        // Выполняем AJAX запрос для получения актуальной цены блюда по названию
        $.ajax({
            url: '/get_unit_price/',  // URL-адрес для получения цены блюда по названию
            data: {
                'dish_name': dishName  // Передаем название выбранного блюда
            },
            success: function(data) {
                // Обновляем значение поля unit_price
                $('#id_unit_price').val(data.unit_price);
            }
        });
    });
});

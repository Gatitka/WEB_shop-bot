document.addEventListener('DOMContentLoaded', function() {
    var textareas = document.querySelectorAll('textarea');

    function autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = (textarea.scrollHeight) + 'px';
    }

    textareas.forEach(function(textarea) {
        autoResizeTextarea(textarea);  // Устанавливаем высоту при загрузке страницы
        textarea.addEventListener('input', function() {
            autoResizeTextarea(textarea);  // Устанавливаем высоту при изменении текста
        });
    });
});

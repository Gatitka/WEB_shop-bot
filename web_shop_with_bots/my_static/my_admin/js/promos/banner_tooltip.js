// форматирует хелп текст кнопки скопировать баннер

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".custom-tooltip").forEach(function (el) {
        el.addEventListener("mouseenter", function () {
            const tooltip = el.querySelector(".tooltip-text");
            if (tooltip) tooltip.style.opacity = "1";
        });
        el.addEventListener("mouseleave", function () {
            const tooltip = el.querySelector(".tooltip-text");
            if (tooltip) tooltip.style.opacity = "0";
        });
    });
});

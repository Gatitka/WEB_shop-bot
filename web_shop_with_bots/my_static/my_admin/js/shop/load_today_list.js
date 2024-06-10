document.addEventListener("DOMContentLoaded", function() {
    var today = new Date();
    var startDate = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 0, 0, 0); // Начало текущего дня
    var endDate = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1, 0, 0, 0); // Начало следующего дня

    var currentUrl = new URL(window.location.href);

    // Проверяем наличие параметров created__gte и created__lt
    var hasCreatedGte = currentUrl.searchParams.has("created__range__gte");
    var hasCreatedLt = currentUrl.searchParams.has("created__range__lt");

    if (!hasCreatedGte) {
        currentUrl.searchParams.set("created__gte", startDate.toISOString());
    }

    if (!hasCreatedLt) {
        currentUrl.searchParams.set("created__lt", endDate.toISOString());
    }

    window.history.replaceState({}, "", currentUrl.toString());
});

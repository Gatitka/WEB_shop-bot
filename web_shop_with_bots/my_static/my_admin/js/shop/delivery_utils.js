// Общие вспомогательные функции для расчёта доставки.
// Используется и в форме создания заказа (add_calculate_delivery.js),
// и в форме изменения заказа (calculate_delivery.js).
// Должен подключаться <script>-тегом РАНЬШЕ обоих файлов выше.

function getCurrentDomain() {
    return window.location.hostname;
}

// URL эндпоинта расчёта доставки под текущий домен
function buildCalculateDeliveryUrl() {
    const domain = getCurrentDomain();
    return domain === '127.0.0.1'
        ? `http://${domain}:8000/api/v1/calculate_delivery/`
        : `https://${domain}/api/v1/calculate_delivery/`;
}

// Стоимость доставки по уже известной (закэшированной на фронте) зоне.
// Используется, когда НЕТ свежего ответа от calculate_delivery/ - при ручном
// выборе зоны в дропдауне, либо при пересчете только из-за изменения суммы
// заказа для уже выбранной зоны.
//
// Это тот же расчет, что get_delivery_cost() делает на бэкенде для обычной
// (не "уточнить") зоны: промо и сумма >= порога -> 0, иначе -> zone.delivery_cost.
//
// ВАЖНО: для зоны "уточнить" бэкенд использует Delivery.default_delivery_cost,
// которого на фронте нет - в этом единственном случае локальный расчет может
// не совпасть со свежим расчетом с бэкенда. Это ожидаемо: "уточнить"
// подставляется бэкендом только когда адрес не попал ни в одну зону по
// координатам - при ручном выборе зоны или пересчете по сумме такого не бывает.
function calcZoneCost(deliveryZone, amount) {
    if (!deliveryZone) return 0;
    if (deliveryZone.is_promo && amount >= deliveryZone.promo_min_order_amount) {
        return 0;
    }
    return parseFloat(deliveryZone.delivery_cost) || 0;
}

// Применяет свежий ответ calculate_delivery/ к полям формы.
// auto_delivery_cost с бэкенда - авторитетное значение (в отличие от
// calcZoneCost() выше, оно уже учитывает, например, случай зоны "уточнить"
// через Delivery.default_delivery_cost) - используем его напрямую, а не
// пересчитываем заново на фронте.
//
// elements: { deliveryZoneSelect, deliveryCostInput, autoDeliveryZoneElement, autoDeliveryCostElement }
// Возвращает новую стоимость доставки (число) либо null, если её не было в ответе.
function applyDeliveryCalcResponse(response, elements) {
    const { deliveryZoneSelect, deliveryCostInput,
            autoDeliveryZoneElement, autoDeliveryCostElement } = elements;

    if (autoDeliveryZoneElement) {
        autoDeliveryZoneElement.value = response.auto_delivery_zone || '';
    }
    if (autoDeliveryCostElement) {
        autoDeliveryCostElement.value = (response.auto_delivery_cost != null)
            ? response.auto_delivery_cost : '';
    }

    // Выставляем зону в дропдауне - по ID, а если его нет в ответе, то по имени
    if (deliveryZoneSelect) {
        let zoneFound = false;

        if (response.auto_delivery_zone_id != null) {
            for (let i = 0; i < deliveryZoneSelect.options.length; i++) {
                if (deliveryZoneSelect.options[i].value == response.auto_delivery_zone_id) {
                    deliveryZoneSelect.selectedIndex = i;
                    zoneFound = true;
                    break;
                }
            }
        }

        if (!zoneFound && response.auto_delivery_zone) {
            for (let i = 0; i < deliveryZoneSelect.options.length; i++) {
                const optionText = deliveryZoneSelect.options[i].text.trim();
                if (optionText === response.auto_delivery_zone ||
                    optionText.startsWith(response.auto_delivery_zone + ',')) {
                    deliveryZoneSelect.selectedIndex = i;
                    break;
                }
            }
        }
    }

    // Стоимость доставки - напрямую из авторитетного ответа бэкенда
    let newCost = null;
    if (deliveryCostInput && response.auto_delivery_cost != null && response.auto_delivery_cost !== '') {
        newCost = parseFloat(response.auto_delivery_cost) || 0;
        deliveryCostInput.value = response.auto_delivery_cost;
    }
    return newCost;
}


// Город заказа - поле city всегда readonly (см. OrderAdmin.readonly_fields),
// поэтому это НЕ <select>, а текст внутри .fieldBox.field-city .readonly -
// одинаково и в форме создания, и в форме изменения заказа.
//
// ВАЖНО: текст в DOM - это отображаемое название ("Novi Sad", с пробелом),
// а не код города, как он хранится в БД ("NoviSad"). Бэкенд
// (/api/v1/calculate_delivery/) сам убирает пробелы при получении -
// смотри city.replace(' ', '') в views.calculate_delivery.
function getOrderCity() {
    const cityField = document.querySelector('.fieldBox.field-city .readonly');
    return cityField ? cityField.textContent.trim() : '';
}

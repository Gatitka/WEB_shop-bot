// Разбивает служебное скрытое поле address_comment
// ("flat: .., floor: .., interfon: ..") на 3 удобных поля админки
// и наоборот. address_comment остаётся hidden-полем и продолжает
// использоваться другими скриптами (выбор "моего адреса" и т.п.)
document.addEventListener('DOMContentLoaded', function () {
    var addressCommentInput = document.getElementById('id_address_comment');
    var flatInput = document.getElementById('id_flat');
    var floorInput = document.getElementById('id_floor');
    var interfonInput = document.getElementById('id_interfon');

    if (!addressCommentInput || !flatInput || !floorInput || !interfonInput) {
        return;
    }

    function parseAddressComment(value) {
        var result = { flat: '', floor: '', interfon: '' };
        if (!value) return result;
        value.split(',').forEach(function (part) {
            var idx = part.indexOf(':');
            if (idx === -1) return;
            var key = part.slice(0, idx).trim().toLowerCase();
            var val = part.slice(idx + 1).trim();
            if (key in result) result[key] = val;
        });
        return result;
    }

    function buildAddressComment(flat, floor, interfon) {
        return 'flat: ' + (flat || '').trim() +
               ', floor: ' + (floor || '').trim() +
               ', interfon: ' + (interfon || '').trim();
    }

    function splitIntoFields() {
        var parsed = parseAddressComment(addressCommentInput.value);
        flatInput.value = parsed.flat;
        floorInput.value = parsed.floor;
        interfonInput.value = parsed.interfon;
    }

    function combineFromFields() {
        addressCommentInput.value = buildAddressComment(
            flatInput.value, floorInput.value, interfonInput.value
        );
    }

    // При первой загрузке: если Django почему-то не проставил initial
    // в 3 поля (например попап "добавить ещё"), раскладываем вручную.
    if (!flatInput.value && !floorInput.value && !interfonInput.value) {
        splitIntoFields();
    }

    // Когда address_comment меняется программно (выбор "моего адреса"
    // в calculate_delivery.js / user_data.js) — раскладываем в 3 поля.
    addressCommentInput.addEventListener('change', splitIntoFields);

    // Когда админ вручную правит кв./этаж/домофон — обновляем hidden-поле.
    [flatInput, floorInput, interfonInput].forEach(function (input) {
        input.addEventListener('input', combineFromFields);
    });
});

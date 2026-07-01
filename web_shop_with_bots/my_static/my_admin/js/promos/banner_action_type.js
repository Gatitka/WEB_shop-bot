/**
 * banner_action_type.js
 */

(function() {
    const ALL_ACTION_FIELDS = [
        'id_dish',
        'id_category',
        'id_url',
        'id_modal_svg',
        'id_modal_svg_ru',
        'id_modal_svg_en',
    ];

    function getField(fieldId) {
        return document.getElementById(fieldId);
    }

    function getBox(fieldId) {
        const el = getField(fieldId);
        if (!el) return null;

        return (
            el.closest('.fieldBox') ||
            el.closest('.form-row') ||
            el.parentElement
        );
    }

    function clearFieldValue(fieldId) {
        const el = getField(fieldId);
        if (!el) return;

        if (el.tagName === 'SELECT') {
            el.value = '';
        } else {
            el.value = '';
        }
    }

    function disableField(fieldId, clearValue = false) {
        const el = getField(fieldId);
        if (!el) return;

        if (clearValue) {
            clearFieldValue(fieldId);
        }

        el.disabled = true;

        const box = getBox(fieldId);
        if (box) {
            box.style.display = 'none';
        }
    }

    function enableField(fieldId) {
        const el = getField(fieldId);
        if (!el) return;

        el.disabled = false;

        const box = getBox(fieldId);
        if (box) {
            box.style.display = '';
        }
    }

    function enableAllFields() {
        ALL_ACTION_FIELDS.forEach(enableField);
    }

    function clearAllFields() {
        ALL_ACTION_FIELDS.forEach(clearFieldValue);
    }

    function disableAllFields(clearValues = false) {
        ALL_ACTION_FIELDS.forEach(fieldId => {
            disableField(fieldId, clearValues);
        });
    }

    function getActiveFields(actionType) {
        if (actionType === 'dish') return ['id_dish'];

        if (actionType === 'category') return ['id_category'];

        if (actionType === 'internal')
            return ['id_url'];

        if (actionType === 'external')
            return ['id_url'];

        if (actionType === 'modal_svg')
            return [
                'id_modal_svg',
                'id_modal_svg_ru',
                'id_modal_svg_en'
            ];

        return [];
    }

    function getFieldsetByTitle(titleText) {
        const fieldsets = document.querySelectorAll('fieldset.module');

        for (const fs of fieldsets) {
            const h2 = fs.querySelector('h2');

            if (h2 && h2.innerText.includes(titleText)) {
                return fs;
            }
        }

        return null;
    }

    function hideModalFieldsets() {
        const modalFs = getFieldsetByTitle(
            'Файлы — модальное окно'
        );

        const modalLangFs = getFieldsetByTitle(
            'Файлы — модальное окно: языковые версии'
        );

        if (modalFs) modalFs.style.display = 'none';

        if (modalLangFs)
            modalLangFs.style.display = 'none';
    }

    function showModalFieldsets() {
        const modalFs = getFieldsetByTitle(
            'Файлы — модальное окно'
        );

        const modalLangFs = getFieldsetByTitle(
            'Файлы — модальное окно: языковые версии'
        );

        if (modalFs) modalFs.style.display = '';

        if (modalLangFs)
            modalLangFs.style.display = '';
    }

    function applyLockedState(actionType, clearValues) {
        const activeFields = getActiveFields(actionType);

        ALL_ACTION_FIELDS.forEach(fieldId => {
            const isActive =
                activeFields.includes(fieldId);

            if (isActive) {
                enableField(fieldId);
            } else {
                disableField(fieldId, clearValues);
            }
        });

        if (actionType === 'modal_svg') {
            showModalFieldsets();
        } else {
            hideModalFieldsets();
        }
    }

    document.addEventListener(
        'DOMContentLoaded',
        function() {
            const actionSelect =
                document.getElementById(
                    'id_action_type'
                );

            if (!actionSelect) return;

            const selected = actionSelect.value;

            if (!selected) {
                enableAllFields();
                hideModalFieldsets();

            } else if (selected === 'none') {
                disableAllFields(false);
                hideModalFieldsets();

            } else {
                applyLockedState(selected, false);
            }

            actionSelect.addEventListener(
                'change',
                function() {
                    const newSelected =
                        actionSelect.value;

                    if (!newSelected) {
                        clearAllFields();
                        enableAllFields();
                        hideModalFieldsets();
                        return;
                    }

                    if (newSelected === 'none') {
                        disableAllFields(true);
                        hideModalFieldsets();
                        return;
                    }

                    clearAllFields();
                    applyLockedState(
                        newSelected,
                        false
                    );
                }
            );
        }
    );
})();

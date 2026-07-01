document.addEventListener('DOMContentLoaded', function () {
    const previewFields = [
        'id_image',
        'id_image_ru',
        'id_image_en',
        'id_modal_svg',
        'id_modal_svg_ru',
        'id_modal_svg_en',
    ];

    function createPreview(input) {
        const row = input.closest('.form-row') || input.closest('.fieldBox');

        const wrapper = document.createElement('div');
        wrapper.className = 'banner-live-preview';

        wrapper.style.position = 'absolute';
        wrapper.style.left = '720px';
        wrapper.style.top = '18px';
        wrapper.style.zIndex = '2';

        const img = document.createElement('img');
        img.style.width = '140px';
        img.style.height = '140px';
        img.style.borderRadius = '8px';
        img.style.objectFit = 'contain';
        img.style.border = '1px solid #444';
        img.style.background = '#111';

        wrapper.appendChild(img);

        if (row) {
            row.style.position = 'relative';
            row.style.minHeight = '175px';
            row.appendChild(wrapper);
        } else {
            input.parentNode.appendChild(wrapper);
        }

        return img;
    }

    previewFields.forEach(function (fieldId) {
        const input = document.getElementById(fieldId);
        if (!input) return;

        let img = null;

        input.addEventListener('change', function () {
            const file = input.files && input.files[0];

            if (!file) {
                if (img) img.parentElement.remove();
                img = null;
                return;
            }

            if (!file.type.startsWith('image/')) return;

            const reader = new FileReader();

            reader.onload = function (e) {
                if (!img) {
                    img = createPreview(input);
                }

                img.src = e.target.result;
            };

            reader.readAsDataURL(file);
        });
    });
});

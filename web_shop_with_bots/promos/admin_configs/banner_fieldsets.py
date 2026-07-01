BANNER_PREVIEW_FIELDSET = (
    'ПРЕВЬЮ: Изображение баннера и модального окна',
    {
        'fields': (
            ('previews_block',),
        )
    }
)


BANNER_ADD_FIELDSETS = [
    ('Основное', {
        'fields': (
            ('title', 'is_active'),
            ('city', 'priority'),
        )
    }),

    ('Интервал показа', {
        'classes': ('collapse',),
        'fields': (
            ('active_from', 'active_until'),
        )
    }),

    ('Действие при клике', {
        'description': (
            'Выберите тип действия и заполните '
            '<b>только одно</b> поле.'
        ),
        'fields': (
            ('action_type',),
            ('dish',),
            ('category',),
            ('url',),
        )
    }),

    ('Файлы — баннер', {
        'fields': (
            ('image',),
        )
    }),

    ('Файлы — баннер: языковые версии', {
        'classes': ('collapse',),
        'fields': (
            ('image_ru',),
            ('image_en',),
        )
    }),

    ('Файлы — модальное окно', {
        'fields': (
            ('modal_svg',),
        )
    }),

    ('Файлы — модальное окно: языковые версии', {
        'classes': ('collapse',),
        'fields': (
            ('modal_svg_ru',),
            ('modal_svg_en',),
        )
    }),
]


BANNER_CHANGE_FIELDSETS = [
    BANNER_PREVIEW_FIELDSET,

    ('Основное', {
        'fields': (
            ('title', 'is_active'),
            ('city', 'priority'),  # 'restaurant',
            ('active_from', 'active_until'),
            ('created', 'updated'),
        )
    }),

    ('Действие при клике', {
        'description': (
            'Выберите тип действия и заполните '
            '<b>только одно</b> поле.'
        ),
        'fields': (
            ('action_type',),
            ('dish',),
            ('category',),
            ('url',),
        )
    }),

    ('Файлы — баннер', {
        'fields': (
            ('image',),
        )
    }),

    ('Файлы — баннер: языковые версии', {
        'classes': ('collapse',),
        'fields': (
            ('image_ru',),
            ('image_en',),
        )
    }),

    ('Файлы — модальное окно', {
        'fields': (
            ('modal_svg',),
        )
    }),

    ('Файлы — модальное окно: языковые версии', {
        'classes': ('collapse',),
        'fields': (
            ('modal_svg_ru',),
            ('modal_svg_en',),
        )
    }),
]

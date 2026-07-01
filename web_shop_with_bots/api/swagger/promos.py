from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


localized_image_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    description=(
        "URL изображения по языкам. "
        "`sr-latn` — дефолтный вариант, "
        "`ru`/`en` — языковые переопределения. "
        "Если языковой вариант не загружен, фронт использует дефолтный."
    ),
    properties={
        "sr-latn": openapi.Schema(
            type=openapi.TYPE_STRING,
            nullable=True,
            example="https://example.com/media/banners/summer.webp",
        ),
        "ru": openapi.Schema(
            type=openapi.TYPE_STRING,
            nullable=True,
            example="https://example.com/media/banners/summer_ru.webp",
        ),
        "en": openapi.Schema(
            type=openapi.TYPE_STRING,
            nullable=True,
            example="https://example.com/media/banners/summer.webp",
        ),
    },
)

localized_modal_svg_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    nullable=True,
    description=(
        "URL SVG модального окна по языкам. "
        "Используется только при `action.type = modal_svg`."
    ),
    properties={
        "sr-latn": openapi.Schema(
            type=openapi.TYPE_STRING,
            nullable=True,
            example="https://example.com/media/banners/svg/promo_sr.svg",
        ),
        "ru": openapi.Schema(
            type=openapi.TYPE_STRING,
            nullable=True,
            example="https://example.com/media/banners/svg/promo_ru.svg",
        ),
        "en": openapi.Schema(
            type=openapi.TYPE_STRING,
            nullable=True,
            example="https://example.com/media/banners/svg/promo_sr.svg",
        ),
    },
)


banner_action_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    description=(
        "Действие при клике на баннер. "
        "Набор дополнительных полей зависит от `type`."
    ),
    properties={
        "type": openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=["dish", "category", "promo_page", "external", "modal_svg", "none"],
            example="dish",
            description=(
                "Тип действия:\n"
                "- `dish` — открыть карточку блюда\n"
                "- `category` — открыть список категории\n"
                "- `promo_page` — открыть внутреннюю промо-страницу\n"
                "- `external` — открыть внешнюю ссылку\n"
                "- `modal_svg` — открыть модальное окно с SVG\n"
                "- `none` — баннер некликабельный"
            ),
        ),
        "dish_article": openapi.Schema(
            type=openapi.TYPE_STRING,
            nullable=True,
            description="Артикул блюда. Только для `type = dish`.",
            example="R001",
        ),
        "category_slug": openapi.Schema(
            type=openapi.TYPE_STRING,
            nullable=True,
            description="Slug категории. Только для `type = category`.",
            example="rolls",
        ),
        "promo_slug": openapi.Schema(
            type=openapi.TYPE_STRING,
            nullable=True,
            description="Slug промо-страницы. Только для `type = promo_page`.",
            example="birthday",
        ),
        "external_url": openapi.Schema(
            type=openapi.TYPE_STRING,
            nullable=True,
            description="Внешняя ссылка. Только для `type = external`.",
            example="https://instagram.com/sushishop",
        ),
        "modal_svg": localized_modal_svg_schema,
    },
    required=["type"],
)


banner_item_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(
            type=openapi.TYPE_INTEGER,
            example=1,
        ),
        "priority": openapi.Schema(
            type=openapi.TYPE_INTEGER,
            nullable=True,
            description="Порядок показа внутри города. Чем меньше — тем раньше в карусели.",
            example=1,
        ),
        "image": localized_image_schema,
        "action": banner_action_schema,
    },
    required=["id", "priority", "image", "action"],
)


banners_list_schema = swagger_auto_schema(
    tags=["Banners"],
    operation_summary="Список баннеров",
    operation_description=(
        "Возвращает баннеры, доступные для показа в клиенте.\n\n"
        "Во view отбираются только:\n"
        "- `is_active = true`\n"
        "- баннеры, попадающие в текущее временное окно `active_from / active_until`\n"
        "- баннеры, ведущие на активные бюда / категории (блюда активны для города+ресторана) / промоновости\n"
        "- сортировка по `city`, затем по `priority`\n\n"
        "Формат ответа:\n"
        "- верхний уровень — объект\n"
        "- ключ — город (`Beograd`, `NoviSad`)\n"
        "- значение — массив баннеров этого города\n\n"
        "Типы действий соответствуют модели Banner.ActionType."
    ),
    responses={
        200: openapi.Response(
            description="Успешный ответ",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description="Словарь баннеров по городам.",
                additional_properties=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=banner_item_schema,
                ),
                example={
                    "Beograd": [
                        {
                            "id": 1,
                            "priority": 1,
                            "image": {
                                "sr-latn": "https://example.com/media/banners/summer.webp",
                                "ru": "https://example.com/media/banners/summer_ru.webp",
                                "en": "https://example.com/media/banners/summer.webp",
                            },
                            "action": {
                                "type": "dish",
                                "dish_article": "R001",
                            },
                        },
                        {
                            "id": 2,
                            "priority": 2,
                            "image": {
                                "sr-latn": "https://example.com/media/banners/promo.webp",
                                "ru": "https://example.com/media/banners/promo.webp",
                                "en": "https://example.com/media/banners/promo.webp",
                            },
                            "action": {
                                "type": "modal_svg",
                                "modal_svg": {
                                    "sr-latn": "https://example.com/media/banners/svg/promo_sr.svg",
                                    "ru": "https://example.com/media/banners/svg/promo_ru.svg",
                                    "en": "https://example.com/media/banners/svg/promo_sr.svg",
                                },
                            },
                        },
                        {
                            "id": 3,
                            "priority": 3,
                            "image": {
                                "sr-latn": "https://example.com/media/banners/cat.webp",
                                "ru": "https://example.com/media/banners/cat_ru.webp",
                                "en": "https://example.com/media/banners/cat_en.webp",
                            },
                            "action": {
                                "type": "category",
                                "category_slug": "rolls",
                            },
                        },
                        {
                            "id": 4,
                            "priority": 4,
                            "image": {
                                "sr-latn": "https://example.com/media/banners/birthday.webp",
                                "ru": "https://example.com/media/banners/birthday_ru.webp",
                                "en": "https://example.com/media/banners/birthday_en.webp",
                            },
                            "action": {
                                "type": "promo_page",
                                "promo_slug": "birthday",
                            },
                        },
                        {
                            "id": 5,
                            "priority": 5,
                            "image": {
                                "sr-latn": "https://example.com/media/banners/instagram.webp",
                                "ru": "https://example.com/media/banners/instagram.webp",
                                "en": "https://example.com/media/banners/instagram.webp",
                            },
                            "action": {
                                "type": "external",
                                "external_url": "https://instagram.com/sushishop",
                            },
                        },
                        {
                            "id": 6,
                            "priority": 6,
                            "image": {
                                "sr-latn": "https://example.com/media/banners/static.webp",
                                "ru": "https://example.com/media/banners/static.webp",
                                "en": "https://example.com/media/banners/static.webp",
                            },
                            "action": {
                                "type": "none",
                            },
                        },
                    ],
                    "NoviSad": [],
                },
            ),
        ),
    },
)

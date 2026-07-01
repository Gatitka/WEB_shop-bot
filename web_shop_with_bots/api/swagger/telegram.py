# api/swagger/telegram.py
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


telegram_link_schema = swagger_auto_schema(
    tags=["Telegram"],
    manual_parameters=[
            openapi.Parameter(
                name="id",
                in_=openapi.IN_QUERY,
                description="Telegram user id",
                type=openapi.TYPE_INTEGER,
                required=True,
            ),
            openapi.Parameter(
                name="first_name",
                in_=openapi.IN_QUERY,
                description="Telegram first name",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                name="last_name",
                in_=openapi.IN_QUERY,
                description="Telegram last name",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                name="username",
                in_=openapi.IN_QUERY,
                description="Telegram username",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                name="photo_url",
                in_=openapi.IN_QUERY,
                description="Telegram user photo",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                name="auth_date",
                in_=openapi.IN_QUERY,
                description="Unix time when auth was made",
                type=openapi.TYPE_INTEGER,
                required=True,
            ),
            openapi.Parameter(
                name="hash",
                in_=openapi.IN_QUERY,
                description="Telegram signature to verify",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
    responses={302: "Redirect to profile",
               400: "Bad signature",
               401: "Unauthorized"},
    operation_summary="Telegram link user account",
    operation_description=(
            "Эндпоинт принимает параметры, которые присылает Telegram Login Widget "
            "через redirect. Берёт город из request.user и по нему выбирает токен нужного бота. "
            "Если подпись валидна — создаёт/обновляет MessengerAccount и привязывает к пользователю. "
            "В конце редиректит обратно в профиль, например /profile?telegram=ok"
        ),
)


telegram_subscription_schema = swagger_auto_schema(
    tags=["Telegram"],
    operation_summary="Telegram bot subscription",
    operation_description="Получает POST с полями tm_id и status и обновляет MessengerAccount.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "tm_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            "status": openapi.Schema(type=openapi.TYPE_BOOLEAN),
        },
        required=["tm_id", "status"],
    ),
    responses={200: "Subscription updated", 400: "Bad request"},
)

telegram_tmauth_schema = swagger_auto_schema(
    tags=["Telegram"],
    operation_summary="Telegram Mini App auth (TMAUTH)",
    operation_description=(
        "Эндпоинт принимает POST из Telegram Mini App.\n\n"
        "1. Принимает raw `initdata` строку от Telegram Mini App.\n"
        "2. По полю `city` выбирает токен нужного телеграм-бота.\n"
        "3. Проверяет подпись/срок жизни данных через `verify_telegram_payload`.\n"
        "4. Находит существующий MessengerAccount по Telegram ID или создаёт новый.\n"
        "5. При необходимости создаёт заглушки `web_account` и `base_profile`.\n"
        "6. Учитывает рекламную кампанию по полю `campaign`.\n"
        "7. Возвращает пару JWT-токенов (`access`, `refresh`).\n\n"
        "Эндпоинт публичный (без авторизации), ботов авторизовать нельзя."
    ),
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "initdata": openapi.Schema(
                type=openapi.TYPE_STRING,
                description=(
                    "Raw `initData` строка от Telegram Mini App "
                    "(URL-закодированная query-строка, как приходит от Telegram)."
                ),
            ),
            "city": openapi.Schema(
                type=openapi.TYPE_STRING,
                description=(
                    "Город/код города, по которому выбирается токен телеграм-бота. "
                    "Например, `bg` или `ns`."
                ),
            ),
            "campaign": openapi.Schema(
                type=openapi.TYPE_STRING,
                description=(
                    "Опциональный код рекламной кампании. "
                    "Если указан, создаётся запись CampaignOpenEvent, "
                    "а для новых пользователей инкрементируется счётчик `campaign.new_users`."
                ),
            ),
            # "start": openapi.Schema(
            #     type=openapi.TYPE_STRING,
            #     description=(
            #         "Опциональный `start`/`start_param` из Telegram deep-link. "
            #         "Прокидывается с клиента, может использоваться для аналитики."
            #     ),
            # ),
            "tg_user": openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description=(
                    "Опциональный объект Telegram-пользователя, продублированный из initData. "
                    "Сервер использует в основном данные из verify_telegram_payload, "
                    "но поле может быть полезно для отладки."
                ),
                properties={
                    "id": openapi.Schema(
                        type=openapi.TYPE_INTEGER,
                        description="Telegram user id",
                    ),
                    "is_bot": openapi.Schema(
                        type=openapi.TYPE_BOOLEAN,
                        description="Флаг, что это бот. Если true — авторизация отклоняется.",
                    ),
                    "first_name": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Имя пользователя в Telegram.",
                    ),
                    "last_name": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Фамилия пользователя в Telegram.",
                    ),
                    "username": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="username в Telegram без @.",
                    ),
                    "language_code": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Язык интерфейса Telegram (например, `ru`).",
                    ),
                    "allows_write_to_pm": openapi.Schema(
                        type=openapi.TYPE_BOOLEAN,
                        description="Разрешает ли пользователь писать ему в личку.",
                    ),
                },
            ),
        },
        required=["initdata", "city"],
        example={
            "initdata": (
                "query_id=AAHKZ5kLAAAAAMpnmQvdFuvN&user=%7B%22id%22%3A194602954%2C"
                "%22first_name%22%3A%22Natalia%22%2C%22last_name%22%3A%22Kirillova%22%2C"
                "%22username%22%3A%22Gatitka5%22%2C%22language_code%22%3A%22ru%22%2C"
                "%22allows_write_to_pm%22%3Atrue%2C%22photo_url%22%3A%22https%3A%5C%2F"
                "%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C%2FxaJQ8xDkAmt7sVUdWuymJZ_"
                "ND10skcA06HrQ2WYyRGo.svg%22%7D&auth_date=1763081137&signature="
                "gqmIUuZbQ0Dfe_NUUlIZMOFtAH5ZNqMWEejyEjTxQQGG-udUNqd34uv0uDK8snGg"
                "G1afTE7LLokFw-Cp4I0sDg&hash=63f0b6f90a2e8900c751c41b02b5057767cc"
                "560de8b8a8e28501ce57f6afd6ac"
            ),
            "campaign": "zsWAhYMj7i",
            "city": "Beograd",
            "tg_user": {
                "id": 795798555515,
                "is_bot": False,
                "first_name": "Nataliaאָלֶף־בֵּית עִבְרִ",
                "last_name": "Kirillova",
                "username": "Gatitka5",
                "allows_write_to_pm": True,
            },
        },
    ),
    responses={
        200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "access": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="JWT access-токен для Mini App / API.",
                ),
                "refresh": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="JWT refresh-токен для обновления пары токенов.",
                ),
            },
            required=["access", "refresh"],
        ),
        400: openapi.Response(
            description=(
                "Некорректные входные данные или ошибка проверки Telegram-подписи.\n\n"
                "Возможные значения `detail`:\n"
                "- `\"init_data required\"` – поле `initdata` не передано.\n"
                "- `\"hash missing\"` – в `initdata` нет параметра `hash`.\n"
                "- `\"bad signature\"` – подпись Telegram не сошлась.\n"
                "- `\"expired\"` – значение `auth_date` устарело (превышен `max_age`)."
            ),
            #schema=error_detail_schema,
            examples={
                "application/json": {
                    "detail": "bad signature"
                }
            },
        ),

        403: openapi.Response(
            description=(
                "Попытка авторизовать Telegram-бота (`is_bot = true`).\n\n"
                "Текст ошибки в поле `detail`:\n"
                "- `\"Bot accounts cannot be authorized or linked.\"`"
            ),
            #schema=error_detail_schema,
            examples={
                "application/json": {
                    "detail": "Bot accounts cannot be authorized or linked."
                }
            },
        ),
    },
)

telegram_me_link_schema = swagger_auto_schema(
    tags=["User", "Telegram"],
    operation_summary="Привязать Telegram-аккаунт к текущему пользователю",
    operation_description=(
        "PATCH /auth/users/me/ для привязки Telegram-аккаунта.\n\n"
        "Эндпоинт принимает обычные поля профиля пользователя "
        "(first_name, last_name, phone и т.п.) и вложенный объект "
        "`messenger_account` с данными из Telegram. "
        "По этим данным создаётся/обновляется MessengerAccount и "
        "привязывается к текущему пользователю."
    ),
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "first_name": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Имя пользователя в нашем сервисе",
            ),
            "last_name": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Фамилия пользователя в нашем сервисе",
            ),
            "email": openapi.Schema(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_EMAIL,
                description="E-mail пользователя в нашем сервисе",
            ),
            "phone": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Телефон пользователя в нашем сервисе",
            ),
            "date_of_birth": openapi.Schema(
                type=openapi.TYPE_STRING,
                format="date",
                nullable=True,
                description="Дата рождения пользователя (опционально)",
            ),
            "city": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Город пользователя в нашем сервисе",
            ),
            "is_subscribed": openapi.Schema(
                type=openapi.TYPE_BOOLEAN,
                description="Согласие на рассылку / подписка",
            ),
            "messenger_account": openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description="Данные Telegram-пользователя для привязки",
                properties={
                    "msngr_type": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Тип мессенджера. Для Telegram, например, `tm`.",
                    ),
                    "id": openapi.Schema(
                        type=openapi.TYPE_INTEGER,
                        description="Telegram user id (числовой ID пользователя в Telegram).",
                    ),
                    "is_bot": openapi.Schema(
                        type=openapi.TYPE_BOOLEAN,
                        description="True, если аккаунт является ботом.",
                    ),
                    "first_name": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Имя в Telegram.",
                    ),
                    "last_name": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Фамилия в Telegram.",
                    ),
                    "username": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="username в Telegram (без @).",
                    ),
                    "auth_date": openapi.Schema(
                        type=openapi.TYPE_INTEGER,
                        description="Unix-время авторизации, из Telegram Login Widget.",
                    ),
                    "hash": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Подпись (hash) от Telegram для проверки подлинности данных.",
                    ),
                    "city": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Город, с которым ассоциируем Telegram-аккаунт.",
                    ),
                    "photo_url": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="URL аватарки пользователя в Telegram.",
                    ),
                },
                required=["msngr_type", "id", "auth_date", "hash"],
            ),
        },
        required=["messenger_account"],
        example={
            "first_name": "NATALIA",
            "last_name": "SUNNOVA",
            "email": "pattikk@yandex.ru",
            "phone": "179355096168",
            "date_of_birth": None,
            "city": "Beograd",
            "is_subscribed": True,
            "messenger_account": {
                "msngr_type": "tm",
                "id": 194629254,
                "is_bot": False,
                "first_name": "Natalia",
                "last_name": "Kirillova",
                "username": "Gatitka5",
                "auth_date": 1763190831,
                "hash": "8e06e74872e3d1cf3cbd3c3e2e58048bb9cbe2b55839b426163d393ce8bd496",
                "city": "Beograd",
                "photo_url": "https://t.me/i/userpic/..."
            },
        },
    ),
    # responses можно не трогать — drf_yasg сам возьмёт схему из сериализатора UserMeSerializer.
)

# api/swagger/registry.py
from functools import lru_cache
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# --- Импортируем все модули со схемами ---
from api.swagger import telegram, promos


@lru_cache
def get_swagger_schema(name: str):
    """Возвращает готовый декоратор по имени."""
    schemas = {
        "telegram_link": telegram.telegram_link_schema,
        "telegram_subscription": telegram.telegram_subscription_schema,
        "telegram_tmauth": telegram.telegram_tmauth_schema,
        "telegram_me_link": telegram.telegram_me_link_schema,
        "banners_list": promos.banners_list_schema,
        # добавляем по мере роста проекта
    }
    if name not in schemas:
        raise KeyError(f"Swagger schema '{name}' is not registered.")
    return schemas[name]

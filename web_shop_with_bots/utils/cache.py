from django.core.cache import cache

def invalidate_menu_cache(city_id=None):
    """
    Сбрасывает кэш меню.
    cache_page генерирует ключ на основе URL, поэтому
    удаляем по паттерну или используем версионирование.
    """
    # Если используешь django-redis:
    keys = cache.keys(f"*menu*")  # или более точный паттерн под твой URL
    if keys:
        cache.delete_many(keys)

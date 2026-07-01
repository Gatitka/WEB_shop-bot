from functools import wraps

from django.conf import settings
from django.core.cache import cache
from rest_framework.response import Response


def cache_response(cache_key_func, timeout=None):
    def decorator(view_method):
        @wraps(view_method)
        def wrapper(view_instance, request, *args, **kwargs):
            cache_key = cache_key_func(
                view_instance,
                request,
                *args,
                **kwargs
            )

            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

            response = view_method(
                view_instance,
                request,
                *args,
                **kwargs
            )

            if (
                response.status_code == 200
                and hasattr(response, "data")
                and request.method == "GET"
            ):
                cache.set(
                    cache_key,
                    response.data,
                    timeout or settings.CACHE_TIME
                )

            return response

        return wrapper

    return decorator

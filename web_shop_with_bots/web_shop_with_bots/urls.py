from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions


schema_view = get_schema_view(
    openapi.Info(
        title="YumeSushi API",
        default_version='v1',
        description="Документация для приложения api проекта YumeSushi",
        contact=openapi.Contact(email="gatitka@yandex.ru"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [

    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),

    # redoc
    re_path(r'^redoc/$',
            schema_view.with_ui('redoc', cache_timeout=0),
            name='schema-redoc'
            ),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

    import debug_toolbar
    urlpatterns += (path('__debug__/', include(debug_toolbar.urls)),)

admin.site.index_title = 'SUSHI SHOP'
# надпись над перечнем админок приложений

admin.site.site_header = 'SUSHI SHOP ADMIN'
# шапка главной страницы админки

admin.site.site_title = 'SUSHI SHOP ADMIN'
# название главной страницы админки

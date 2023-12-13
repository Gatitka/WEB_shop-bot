from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.static import static
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
    re_path(r'^redoc/$',
            schema_view.with_ui('redoc', cache_timeout=0),
            name='schema-redoc'
            ),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

admin.site.index_title = 'SUSHI SHOP'
# надпись над перечнем админок приложений

admin.site.site_header = 'SUSHI SHOP ADMIN'
# шапка главной страницы админки

admin.site.site_title = 'SUSHI SHOP ADMIN'
# название главной страницы админки

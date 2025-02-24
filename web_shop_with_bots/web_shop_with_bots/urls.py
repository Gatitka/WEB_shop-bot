from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from api import admin_views


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
from django.http import JsonResponse

def trigger_error(request):
    division_by_zero = 1 / 0
    # try:
    #     division_by_zero = 1 / 0
    # except Exception as e:
    #     # Логируем ошибку (необязательно, но полезно для отладки)
    #     print(f"Error occurred: {str(e)}")

    #     # Возвращаем JsonResponse с информацией об ошибке и статусом 500 (Server Error)
    #     return JsonResponse({'error': 'Division by zero error'}, status=500)

    # # Если исключение не возникло, возвращаем успешный JsonResponse (это зависит от логики вашего приложения)
    # return JsonResponse({'message': 'Success'})

urlpatterns = [
    path('admin/sales-data/', admin_views.sales_data, name='sales_data'),
    path('admin/receipt/formatted/<int:order_id>/',
         admin_views.get_formatted_receipt, name='formatted-receipt'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('sentry-debug/', trigger_error),

    path('summernote/', include('django_summernote.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
    urlpatterns += (    # redoc
                    re_path(r'^redoc/$',
                            schema_view.with_ui('redoc', cache_timeout=0),
                            name='schema-redoc'),)
    import debug_toolbar
    urlpatterns += (
                    path('__debug__/',
                         include(debug_toolbar.urls)),)


admin.site.index_title = 'SUSHI SHOP'
# надпись над перечнем админок приложений

admin.site.site_header = 'SUSHI SHOP ADMIN'
# шапка главной страницы админки

admin.site.site_title = 'SUSHI SHOP ADMIN'
# название главной страницы админки

"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

# Schema configuration for API documentation
schema_view = get_schema_view(
    openapi.Info(
        title="Futures Screener API",
        default_version='v1',
        description="""
        🚀 **Futures Screener API** - система мониторинга и анализа криптовалютных рынков

        ## Основные возможности:

        ### 📊 Анализ рынка
        - Получение текущих цен спот и фьючерсов ETH/BTC
        - Технический анализ собственного движения активов
        - Исторические данные с различных таймфреймов
        - Построение графиков и аналитика

        ### ⚠️ Система алертов
        - Создание персональных ценовых алертов
        - Мгновенное уведомление при достижении целевых цен
        - Управление списком алертов

        ### 🔐 Аутентификация
        - JWT аутентификация
        - Регистрация и управление профилем
        - Ролевая модель доступа (пользователь/менеджер)

        ## Токен авторизации
        Для доступа к защищенным endpoint'ам добавьте в заголовки:
        ```
        Authorization: Bearer <your_jwt_token>
        ```

        ## Поддержка символов
        - ETHUSDT (Ethereum)
        - BTCUSDT (Bitcoin)

        ## Категории данных
        - spot (спотовые цены)
        - linear (линейные фьючерсы)
        - inverse (обратные фьючерсы)
        """,
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="support@futures-screener.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Main pages
    path("", TemplateView.as_view(template_name="home.html"), name="home"),

    # Apps
    path("users/", include("users.urls", namespace="users")),
    path('screener/', include('screener.urls')),

    # API Documentation
    path('swagger.json',
         schema_view.without_ui(cache_timeout=0),
         name='schema-json'),
    path('swagger.yaml',
         schema_view.without_ui(cache_timeout=0),
         name='schema-yaml'),
    path('swagger/',
         schema_view.with_ui('swagger', cache_timeout=0),
         name='schema-swagger-ui'),
    path('redoc/',
         schema_view.with_ui('redoc', cache_timeout=0),
         name='schema-redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
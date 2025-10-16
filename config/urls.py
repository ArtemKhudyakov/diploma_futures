from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

# Настройка схемы API
schema_view = get_schema_view(
    openapi.Info(
        title="Habit Tracker API",
        default_version="v1",
        description="API для трекера полезных привычек",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@habittracker.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny, ],
)

urlpatterns = [
                  path("admin/", admin.site.urls),
                  path("", TemplateView.as_view(template_name="home.html"), name="home"),
                  path("users/", include("users.urls", namespace="users")),
                  path('screener/', include('screener.urls')),
                  # path("swagger.json", schema_view.without_ui(cache_timeout=0), name="schema-json"),
                  # path("swagger.yaml", schema_view.without_ui(cache_timeout=0), name="schema-yaml"),
                  # path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
                  # path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

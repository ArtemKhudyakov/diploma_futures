from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

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

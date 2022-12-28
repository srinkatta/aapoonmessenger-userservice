"""user_service URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from user_service.router_urls import router_urlpatterns

urlpatterns = [
    path("admin/", admin.site.urls),
    path("/users/api/", include(router_urlpatterns)),
    path("/users/api-auth/", include("rest_framework.urls")),
    path("users/accounts/", include("allauth.urls")),
    path("users/api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Optional UI:
    path(
        "users/api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "users/api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

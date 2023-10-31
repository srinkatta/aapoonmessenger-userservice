"""user_service URL Configuration
"""
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from django.conf import settings
from django.conf.urls.static import static
from user_service.router_urls import router_urlpatterns

urlpatterns = [
    path("api/users/", include(router_urlpatterns)),
    path("/api-auth/users/", include("rest_framework.urls")),
    path("accounts/users/", include("allauth.urls")),
    path("api/users/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Optional UI:
    path(
        "api/users/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/users/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]


urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

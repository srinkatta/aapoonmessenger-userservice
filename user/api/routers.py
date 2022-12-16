from rest_framework import routers
from django.urls import path, include
from rest_framework_simplejwt import views as jwt_views

from user.api.viewsets import AuthUserRegistrationView, AuthUserLoginView

router = routers.SimpleRouter()

urlpatterns = [
    path(r"auth/", include(router.urls)),
    path(
        "auth/token/obtain/",
        jwt_views.TokenObtainPairView.as_view(),
        name="token_create",
    ),
    path(
        "auth/token/refresh/",
        jwt_views.TokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path(
        "auth/token/verify/", jwt_views.TokenVerifyView.as_view(), name="token_verify"
    ),
    path("auth/register/", AuthUserRegistrationView.as_view(), name="register"),
    path("auth/login/", AuthUserLoginView.as_view(), name="login"),
]

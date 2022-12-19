from rest_framework import routers
from django.urls import path, include
from rest_framework_simplejwt import views as jwt_views
from user.api.viewsets import (
    AuthUserRegistrationView,
    AuthUserLoginView,
    UserLogsViewSet,
    UserFeedbackViewSet,
    UserDeviceViewSet,
    UserInviteViewSet,
    UserProfileViewSet,
)

from user.api.kyc import viewsets as kyc_viewsets

router = routers.SimpleRouter()
router.register(r"profile", UserProfileViewSet, basename="user_profile"),
router.register(r"logs", UserLogsViewSet, basename="user_logs"),
router.register(r"feedback", UserFeedbackViewSet, basename="user_feedback"),
router.register(r"invite", UserInviteViewSet, basename="user_invite"),
router.register(r"device", UserDeviceViewSet, basename="user_device")

urlpatterns = [
    path(r"", include(router.urls)),
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
    # KYC urls
    path("selfie/", kyc_viewsets.SelfieViewSet.as_view(), name="selfie"),
    path(
        "photo_id/verification/",
        kyc_viewsets.PhotoIDVerifyViewSet.as_view(),
        name="photo_id_verification",
    ),
    path(
        "profile/",
        kyc_viewsets.ProfileUpdateViewSet.as_view(),
        name="profile_picture_update",
    ),
    path(
        "kyc/verification/",
        kyc_viewsets.ComparefacesViewSet.as_view(),
        name="kyc_verification",
    ),
]

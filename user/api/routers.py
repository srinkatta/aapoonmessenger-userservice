from rest_framework import routers
from django.urls import path, include
from rest_framework_simplejwt import views as jwt_views
from user.api.viewsets import (
    AuthUserRegistrationView,
    AuthUserLoginView,
    UserLogsViewSet,
    UserDeviceViewSet,
    UserInviteViewSet,
    UserProfileViewSet,
    UserViewSet,
    PushNotificationSettings,
    SendOTPView,
    VerifyPhoneView,
    DeviceInfoView,
    LanguageView,
    FeedbackView,
    UserDeleteView,
    UserDeleteRevokeView,
    InviteListView,
    UserDetailsAPI,
    UserDetailsPhoneAPI,
)

from user.api.kyc import viewsets as kyc_viewsets

router = routers.SimpleRouter()
router.register(r"user", UserViewSet, basename="user"),
router.register(r"profile", UserProfileViewSet, basename="user_profile"),
router.register(r"logs", UserLogsViewSet, basename="user_logs"),
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
    path("auth/send_otp/", SendOTPView.as_view(), name="send_otp"),
    path("auth/verify_otp/", VerifyPhoneView.as_view(), name="verify_otp"),
    path(
        "notify_settings/",
        PushNotificationSettings.as_view(),
        name="push_notification_settings",
    ),
    # KYC urls
    path("selfie/", kyc_viewsets.SelfieViewSet.as_view(), name="selfie"),
    path(
        "photo_id/verification/",
        kyc_viewsets.PhotoIDVerifyViewSet.as_view(),
        name="photo_id_verification",
    ),
    path(
        "profile_update/",
        kyc_viewsets.ProfileUpdateViewSet.as_view(),
        name="profile_picture_update",
    ),
    path(
        "kyc/verification/",
        kyc_viewsets.ComparefacesViewSet.as_view(),
        name="kyc_verification",
    ),
    path(
        "kyc_upload/",
        kyc_viewsets.KYCUploadViewSet.as_view({"get": "list"}),
        name="kyc_upload",
    ),
    path(
        "feedback_upload/",
        kyc_viewsets.FeedbackUploadViewSet.as_view({"get": "list"}),
        name="feedback_upload",
    ),
    path("device_info/", DeviceInfoView.as_view(), name="device_info"),
    path("user_delete/", UserDeleteView.as_view(), name="user_delete"),
    path(
        "user/delete/revoke/", UserDeleteRevokeView.as_view(), name="user_delete_revoke"
    ),
    path("lang/", LanguageView.as_view(), name="language_detect"),
    path("feedback/", FeedbackView.as_view(), name="feedback"),
    path("invite_list/", InviteListView.as_view(), name="get_invite_list"),
    path("user_details/", UserDetailsAPI.as_view(), name="user_details"),
    path(
        "user_details/phone/", UserDetailsPhoneAPI.as_view(), name="user_details_phone"
    ),
]

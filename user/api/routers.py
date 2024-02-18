from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt import views as jwt_views

from user.api.admin import viewsets as admin_viewsets
from user.api.direct_messages.viewsets import (
    MuteMessageView,
    NotifyRedirectDmViewSet,
    UserChatDeleteView,
    XMPPMonthlyChatViewSet,
)
from user.api.kyc import viewsets as kyc_viewsets
from user.api.viewsets import (
    AppPolicyView,
    AuthUserLoginView,
    AuthUserRegistrationView,
    DeviceInfoView,
    FeedbackView,
    GetAssociatedUsers,
    InviteListView,
    PushNotificationSettings,
    SendOTPView,
    UserCheckAPIView,
    UserDeleteCronView,
    UserDeleteRevokeView,
    UserDeleteRequestView,
    UserDeleteRequestList,
    UserDetailsAPI,
    UserDetailsPhoneAPI,
    UserDeviceViewSet,
    UserInviteViewSet,
    UserLogsViewSet,
    UserProfileSearchAPI,
    UserProfileViewSet,
    UserViewSet,
    VerifyPhoneView,
    SubmitPollData,
)

router = routers.SimpleRouter()
router.register(r"user", UserViewSet, basename="user"),
router.register(r"profile", UserProfileViewSet, basename="user_profile"),
router.register(r"logs", UserLogsViewSet, basename="user_logs"),
router.register(r"invite", UserInviteViewSet, basename="user_invite"),
router.register(r"device", UserDeviceViewSet, basename="user_device")
router.register(
    r"admin-panel/app_policy", admin_viewsets.AppPolicyViewSet, basename="App Policy"
),
router.register(
    r"admin-panel/app_info", admin_viewsets.AppInfoViewSet, basename="App Info"
),

urlpatterns = [
    path("admin/", admin.site.urls),
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
    path("device_info/", DeviceInfoView.as_view(), name="device_info"),
    path("user_delete/", UserDeleteRequestView.as_view(), name="user_delete"),
    path(
        "delete-requests/", UserDeleteRequestList.as_view(), name="deleted_users_list"
    ),
    path("associated/", GetAssociatedUsers.as_view(), name="role-associated-users"),
    path(
        "user/delete/revoke/", UserDeleteRevokeView.as_view(), name="user_delete_revoke"
    ),
    path("user_delete/cron/", UserDeleteCronView.as_view(), name="user_delete_cron"),
    path("app_policy/", AppPolicyView.as_view(), name="app_policy"),
    path("feedback/", FeedbackView.as_view(), name="feedback"),
    path("invite_list/", InviteListView.as_view(), name="get_invite_list"),
    path("user_details/", UserDetailsAPI.as_view(), name="user_details"),
    path(
        "user_details_phone/", UserDetailsPhoneAPI.as_view(), name="user_details_phone"
    ),
    path("user_friends_check/", UserCheckAPIView.as_view(), name="user_friends_check"),
    path(
        "notify_settings/",
        PushNotificationSettings.as_view(),
        name="push_notification_settings",
    ),
    path(
        "profile_search/",
        UserProfileSearchAPI.as_view(),
        name="user_profile_search",
    ),
    path("poll_data/", SubmitPollData.as_view(), name="submit_poll_data"),
    # Direct message urls
    path("notify_dm/", NotifyRedirectDmViewSet.as_view(), name="notify_redirect_dm"),
    path("mute_messages/", MuteMessageView.as_view(), name="mute_messages"),
    path(
        r"xmpp_monthly_chat/",
        XMPPMonthlyChatViewSet.as_view({"get": "list"}),
        name="xmpp_chat",
    ),
    path(r"user_chat_delete/", UserChatDeleteView.as_view(), name="user_chat_delete"),
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
    # Admin Panel urls
    path(
        "admin-panel/register/",
        admin_viewsets.AdminPanelRegisterAPI.as_view(),
        name="Admin Panel Register",
    ),
    path(
        "admin-panel/login/",
        admin_viewsets.AdminPanelLoginAPI.as_view(),
        name="Admin Panel Login",
    ),
    path(
        "admin-panel/users/",
        admin_viewsets.UserListDetailsAPI.as_view(),
        name="UserListAPI",
    ),
    path(
        "admin-panel/verify/settings/",
        admin_viewsets.UserVerificationSettingAPI.as_view(),
        name="UserVerificationSettingAPI",
    ),
    path(
        "admin-panel/users/filter/",
        admin_viewsets.AdminUserFilters.as_view(),
        name="UserFilterAPI",
    ),
    path(
        "admin-panel/user/delete/",
        admin_viewsets.UserDeleteAdminAPI.as_view(),
        name="UserDeleteAdminAPI",
    ),
    path(
        "admin-panel/export/data/",
        admin_viewsets.UsersExportAPI.as_view(),
        name="Export User Data",
    ),
    path(
        "admin-panel/deleted/users/",
        admin_viewsets.DeletedUserAPI.as_view(),
        name="Deleted Users",
    ),
]

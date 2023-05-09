from user.api.admin import viewsets as admin_viewsets
from django.urls import path, include
from rest_framework import routers


admin_router = routers.SimpleRouter()
admin_router.register(
    r"app_policy", admin_viewsets.AppPolicyViewSet, basename="App Policy"
),
admin_router.register(
    r"app_info", admin_viewsets.AppInfoViewSet, basename="App Policy"
),

urlpatterns = [
    path(
        "superuser/register/",
        admin_viewsets.RegisterSuperUserAPI.as_view(),
        name="Super User Creation",
    ),
    path(
        "superuser/login/",
        admin_viewsets.SuperUserLoginAPI.as_view(),
        name="Super User Login",
    ),
    path("", include(admin_router.urls)),
    path("users/", admin_viewsets.UserListDetailsAPI.as_view(), name="UserListAPI"),
    # path("user_detail/<int:pk>/", UserDetailAPI.as_view(), name="UserDetailAPI"),
    path(
        "verify_settings/",
        admin_viewsets.UserVerificationSettingAPI.as_view(),
        name="UserVerificationSettingAPI",
    ),
    path(
        "users-filter/", admin_viewsets.AdminUserFilters.as_view(), name="UserFilterAPI"
    ),
    path(
        "user_delete/",
        admin_viewsets.UserDeleteAdminAPI.as_view(),
        name="UserDeleteAdminAPI",
    ),
    path(
        "export-data/", admin_viewsets.UsersExportAPI.as_view(), name="Export User Data"
    ),
    path(
        "deleted_users/", admin_viewsets.DeletedUserAPI.as_view(), name="Deleted Users"
    ),
]

from django.contrib import admin

from user.models import (
    User,
    UserLog,
    UserFeedback,
    UserInvite,
    UserDevice,
    UserKycSetting,
    UserProfile,
    UserPhoneVerification,
)

admin.site.register(UserLog)
admin.site.register(UserFeedback)
admin.site.register(UserInvite)
admin.site.register(UserDevice)
admin.site.register(UserKycSetting)
admin.site.register(UserProfile)
admin.site.register(UserPhoneVerification)


class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "email",
        "date_joined",
        "phone_number",
        "phone_number_verified",
    )
    list_display_links = ["id", "name"]
    readonly_fields = []
    list_per_page = 50
    line_numbering = 0

    def name(self, instance):
        return instance.name


admin.site.register(User, UserAdmin)

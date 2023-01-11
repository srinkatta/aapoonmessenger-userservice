import re

from django.contrib import admin
from django.utils.safestring import mark_safe

from user.models import (
    User,
    UserLog,
    UserFeedback,
    UserInvite,
    UserDevice,
    UserKycSetting,
    UserProfile,
    UserPhoneVerification,
    DeviceInfo,
    AppInfo,
    Languages,
    DeletedUser,
)

admin.site.register(UserLog)
admin.site.register(UserFeedback)
admin.site.register(UserInvite)
admin.site.register(UserDevice)
admin.site.register(UserKycSetting)
admin.site.register(UserProfile)
admin.site.register(UserPhoneVerification)
admin.site.register(DeviceInfo)
admin.site.register(AppInfo)
admin.site.register(Languages)
admin.site.register(DeletedUser)


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
    list_per_page = 50
    line_numbering = 0
    readonly_fields = ["logo", "source_image", "kyc_logs_history"]
    search_fields = ("first_name", "last_name", "email", "phone_number")
    exclude = ("groups", "user_permissions")
    fieldsets = (
        (
            "KYC Info",
            {
                "fields": (
                    ("first_name", "last_name", "email"),
                    ("phone_number", "phone_number_verified"),
                    # ("logo", "secondary_picture"),
                )
            },
        ),
        (
            "KYC Logs",
            {
                "classes": ("collapse",),
                "fields": ("kyc_logs_history",),
            },
        ),
        (
            "KYC Images",
            {
                "classes": ("collapse",),
                "fields": ("source_image",),
            },
        ),
        (
            "Other Info",
            {
                "classes": ("collapse",),
                "fields": ("last_login", "is_active"),
            },
        ),
    )

    def name(self, instance):
        return instance.name

    def kyc_logs(self, user):
        return user.logs.get().kyc_logs

    def kyc_logs_history(self, user):
        return mark_safe(self.kyc_logs(user))

    def source_image(self, user):
        if self.kyc_logs(user):
            urls = self.findUrl(self.kyc_logs(user))
            parsed_urls = []
            html_string = ""
            try:
                if urls and len(urls):
                    for url in urls:
                        url = url.replace("</strong>", "")
                        url = url.replace("</span>", "")
                        url = url.replace("<br", " ")
                        url = url.replace("<b>", " ")
                        url = url.replace("</b>", " ")
                        parsed_urls.append(url)
                    for i in list(divide_chunks(parsed_urls, 1)):
                        html_string += """<div style="display:flex"><div style="flex: 33.33%; padding: 5px"><img width=500 '
                               'height=500 src="{url}" /></div>""".format(
                            url=i[0],
                        )
                    return mark_safe(html_string)
            except Exception as e:
                print("Exception: %s", e)
        return "<div>No images uploaded.</div>"

    def findUrl(self, string):
        url = re.findall(r"(https?://[^\s]+)", string)
        return url


def divide_chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i : i + n]


admin.site.register(User, UserAdmin)

import re
import logging

from datetime import timedelta
from django.utils import timezone
from django.contrib import admin
from django.db import connections
from django.utils.safestring import mark_safe

from django_admin_listfilter_dropdown.filters import DropdownFilter

from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.fields import Field

from rangefilter.filter import DateRangeFilter
import pandas as pd

from user_service import settings
from user.utils import make_request
from user.models import (
    User,
    UserLog,
    UserInvite,
    UserDevice,
    UserVerificationSetting,
    UserProfile,
    DeviceInfo,
    AppInfo,
    Languages,
    DeletedUser,
)

admin.site.register(UserLog)
admin.site.register(UserInvite)
admin.site.register(UserDevice)
admin.site.register(UserProfile)
admin.site.register(DeviceInfo)
admin.site.register(AppInfo)
admin.site.register(Languages)
admin.site.register(DeletedUser)


class UserResource(resources.ModelResource):
    phone_number_verified = Field()
    kyc_done = Field()
    name = Field()
    user_type = Field()

    class Meta:
        model = User
        fields = (
            "id",
            "name",
            "email",
            "date_joined",
            "country_code",
            "phone_number",
            "phone_number_verified",
            "kyc_done",
            "user_type",
        )
        export_order = fields

    def dehydrate_phone_number_verified(self, user):
        return True if user.phone_number_verified else False

    def dehydrate_kyc_done(self, user):
        return user.settings.get().kyc_done

    def dehydrate_name(self, user):
        user = User.objects.filter(id=user.id).first()
        if user:
            return user.name
        return ""

    def dehydrate_user_type(self, user):
        user = User.objects.filter(id=user.id).first()
        return user.user_type


class UsertypeFilter(admin.SimpleListFilter):
    title = "User Type"
    parameter_name = "user_type"

    def lookups(self, request, model_admin):
        return (
            ("Individual User", "Individual User"),
            ("Business User", "Business User"),
        )

    def queryset(self, request, queryset):
        if self.value() == "Individual User":
            return queryset.filter(user_type="individualuser", is_business=False, phone_number_verified=True)
        elif self.value() == "Business User":
            return queryset.filter(user_type="businessuser", is_business=True, phone_number_verified=True)


class LastWeekMonthLastLoginFilter(admin.SimpleListFilter):
    title = "Last Login"
    parameter_name = "last_login"

    def lookups(self, request, model_admin):
        return (
            ("last_week", "Last Week"),
            ("last_month", "Last Month"),
        )

    def queryset(self, request, queryset):
        if self.value() == "last_week":
            last_week_date = timezone.now().date() - timedelta(days=7)
            return queryset.filter(last_login__gte=last_week_date)
        elif self.value() == "last_month":
            last_month_date = timezone.now().date() - timedelta(days=30)
            return queryset.filter(last_login__gte=last_month_date)
        return queryset


class KycDoneFilter(admin.SimpleListFilter):
    title = "Kyc Verified"
    parameter_name = "kyc_done"

    def lookups(self, request, model_admin):
        return (
            ("Yes", "Yes"),
            ("No", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == "Yes":
            return queryset.filter(kyc_done=True)
        elif self.value() == "No":
            return queryset.filter(kyc_done=False)


class KycVerifiedFilter(admin.SimpleListFilter):
    title = "Kyc Verified"
    parameter_name = "kyc_done"

    def lookups(self, request, model_admin):
        return (
            ("Yes", "Yes"),
            ("No", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == "Yes":
            with connections["default"].cursor() as db_cursor:
                query = """SELECT user.id FROM user_user user 
                JOIN user_userverificationsetting settings 
                ON user.id=settings.user_id 
                WHERE settings.kyc_done=true"""
                db_cursor.execute(query)
                table_rows = db_cursor.fetchall()
                df = pd.DataFrame(table_rows)
                values = df[0].tolist()
                return queryset.filter(pk__in=values)
        elif self.value() == "No":
            with connections["default"].cursor() as db_cursor:
                query = """SELECT user.id FROM user_user user
                 JOIN user_userverificationsetting settings 
                 ON user.id=settings.user_id 
                 WHERE settings.kyc_done=false"""
                db_cursor.execute(query)
                table_rows = db_cursor.fetchall()
                df = pd.DataFrame(table_rows)
                values = df[0].tolist()
                return queryset.filter(pk__in=values)
        return queryset


def source_images(kyc_logs):
    if kyc_logs:
        urls = findUrl(kyc_logs)
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


def findUrl(string):
    url = re.findall(r"(https?://[^\s]+)", string)
    return url


class UserAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = UserResource
    extra_css = {"all": ["css/admin_logout_option.css"]}
    list_display = (
        "id",
        "name",
        "email",
        "date_joined",
        "country_iso",
        "phone_number",
        "phone_number_verified",
        "kyc_done",
        "user_type_validate",
    )
    list_display_links = ["id", "name"]
    list_per_page = 50
    line_numbering = 0
    readonly_fields = ["logo", "source_image", "kyc_logs_history"]
    search_fields = ("name", "email", "" "phone_number")
    actions = ["delete_users"]
    exclude = ("groups", "user_permissions")
    list_filter = (
        ("date_joined", DateRangeFilter),
        ("country_iso_code", DropdownFilter),
        "phone_number_verified",
        KycVerifiedFilter,
        LastWeekMonthLastLoginFilter,
        UsertypeFilter,
    )

    fieldsets = (
        (
            "KYC Info",
            {
                "fields": (
                    ("name", "email"),
                    ("phone_number_verified",),
                    (
                        "country_code",
                        "phone_number",
                    ),
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

    def country_iso(self, user):
        return user.country_iso_code

    def name(self, instance):
        return f"{instance.name}"

    def user_type_validate(self, instance):
        if instance.phone_number_verified:
            return instance.user_type
        else:
            return ""

    def kyc_logs(self, user):
        return user.logs.get().kyc_logs

    def kyc_done(self, user):
        return user.settings.get().kyc_done

    def is_business(self, user):
        return user.is_business

    def kyc_logs_history(self, user):
        return mark_safe(self.kyc_logs(user))

    def source_image(self, user):
        kyc_logs = self.kyc_logs(user)
        if kyc_logs:
            return source_images(kyc_logs)

    def delete_users(self, request, queryset):
        for user in queryset:
            # Make a Web Socket call to Unregister user from ejabberd
            phone_number = "{}{}".format(user.country_code, user.phone_number)
            endpoint = "{}{}".format(settings.XMPP_SERVER_URL, "api/unregister/")
            data = {"user": phone_number, "host": settings.XMPP_HOST}
            try:
                make_request(endpoint, "POST", data=data)
                logging.info("User successfully unregistered at websocket server")
            except Exception as e:
                logging.debug("Error unregistering user at websocket server %s" % e)
            users = User.objects.filter(id=user.id).first()
            delete_user = DeletedUser(user=users, is_deleted=True)
            delete_user.save()
            user.delete()
            return delete_user

    kyc_done.boolean = True
    kyc_done.short_description = "kyc verified"
    user_type_validate.short_description = "user type"
    country_iso.short_description = "country"


def divide_chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i : i + n]


admin.site.register(User, UserAdmin)


class UserVerificationSettingAdmin(admin.ModelAdmin):
    list_filter = (KycDoneFilter,)
    search_fields = ("user__id", "user__phone_number")
    list_display = (
        "user_id",
        "name",
        "phone",
        "kyc_done",
    )
    readonly_fields = ["source_image", "kyc_logs_history"]

    fieldsets = (
        (
            "KYC Info",
            {
                "fields": (
                    "kyc_done",
                    "photo_id",
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
    )

    def user_id(self, instance):
        return instance.user.id

    def name(self, instance):
        return instance.user.name

    def phone(self, instance):
        return instance.user.phone_number

    def kyc_logs(self, instance):
        return instance.user.logs.get().kyc_logs

    def kyc_logs_history(self, user):
        return mark_safe(self.kyc_logs(user))

    def source_image(self, user):
        kyc_logs = self.kyc_logs(user)
        if kyc_logs:
            return source_images(kyc_logs)


admin.site.register(UserVerificationSetting, UserVerificationSettingAdmin)

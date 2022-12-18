from django.contrib.auth.models import AbstractUser
from django.db import models

from user.choices import COUNTRY_CODE_CHOICES


class User(AbstractUser):
    country_iso_code = models.CharField(max_length=255, null=True, blank=True)
    country_code = models.CharField(
        max_length=10, choices=COUNTRY_CODE_CHOICES, null=True
    )
    phone_number = models.CharField(max_length=30, null=True)
    phone_number_verified = models.BooleanField(
        verbose_name="Phone Verified", default=False
    )
    user_type = models.CharField(max_length=15, null=True)
    profile_pic = models.URLField(max_length=255, null=True, blank=True)
    second_last_login = models.DateTimeField(null=True, blank=True)
    additional_last_login = models.DateTimeField(null=True, blank=True)
    online_status = models.BooleanField(default=False)
    jid = models.URLField(max_length=255, null=True, blank=True)
    fcm_token = models.CharField(max_length=100, null=True, blank=True)
    apns_token = models.CharField(max_length=100, null=True, blank=True)
    otp_requested = models.CharField(max_length=100, null=True, blank=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"


class UserLogs(models.Model):
    s3_logs = models.CharField(max_length=100, null=True, blank=True)
    kyc_logs = models.CharField(max_length=100, null=True, blank=True)
    user = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.user}"

    class Meta:
        verbose_name = 'UserLog'
        verbose_name_plural = 'UserLogs'


class UserFeedback(models.Model):
    feedback = models.CharField(max_length=100, null=True, blank=True)
    user = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.user}"

    class Meta:
        verbose_name = 'UserFeedback'
        verbose_name_plural = 'UserFeedbacks'


class UserInvite(models.Model):
    invite_token = models.CharField(max_length=100, null=True, blank=True)
    invite_code = models.CharField(max_length=100, null=True, blank=True)
    group_code = models.CharField(max_length=100, null=True, blank=True)
    user = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.user}"

    class Meta:
        verbose_name = 'UserInvite'
        verbose_name_plural = 'UserInvites'


class UserDevice(models.Model):
    device_model = models.CharField(max_length=100, null=True, blank=True)
    device_os_version = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.user}"

    class Meta:
        verbose_name = 'UserDevice'
        verbose_name_plural = 'UserDevices'


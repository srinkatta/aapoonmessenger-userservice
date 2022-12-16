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

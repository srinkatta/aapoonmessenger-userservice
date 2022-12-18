from django.contrib.auth.models import AbstractUser
from django.db import models

from common.models import BaseTimeStampedModel
from user.choices import (
    COUNTRY_CODE_CHOICES,
    EDUCATION_CHOICES,
    INCOME_CHOICES,
    MARITAL_STATUS_CHOICES,
    INTEREST_CHOICES,
    SPORTS_CHOICES,
    GENDER_CHOICES,
    SECTORS_TYPE_CHOICES,
)

from multiselectfield import MultiSelectField


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
        return f"ID: {self.id}, Name: {self.first_name} {self.last_name}"

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"


class UserLog(BaseTimeStampedModel):
    s3_logs = models.CharField(max_length=100, null=True, blank=True)
    kyc_logs = models.CharField(max_length=100, null=True, blank=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="logs",
    )

    def __str__(self):
        return f"{self.user}"

    class Meta:
        verbose_name = "UserLog"
        verbose_name_plural = "UserLogs"


class UserFeedback(BaseTimeStampedModel):
    feedback = models.CharField(max_length=100, null=True, blank=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="feedback",
    )

    def __str__(self):
        return f"{self.user}"

    class Meta:
        verbose_name = "UserFeedback"
        verbose_name_plural = "UserFeedbacks"


class UserInvite(BaseTimeStampedModel):
    invite_token = models.CharField(max_length=100, null=True, blank=True)
    invite_code = models.CharField(max_length=100, null=True, blank=True)
    group_code = models.CharField(max_length=100, null=True, blank=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="invites",
    )

    def __str__(self):
        return f"{self.user}"

    class Meta:
        verbose_name = "UserInvite"
        verbose_name_plural = "UserInvites"


class UserDevice(BaseTimeStampedModel):
    device_model = models.CharField(max_length=100, null=True, blank=True)
    device_os_version = models.CharField(max_length=100, null=True, blank=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="devices",
    )

    def __str__(self):
        return f"{self.user}"

    class Meta:
        verbose_name = "UserDevice"
        verbose_name_plural = "UserDevices"


class UserPhoneVerification(BaseTimeStampedModel):
    country_code = models.CharField(
        max_length=10,
        choices=COUNTRY_CODE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Updated Country Code",
    )
    phone_number = models.CharField(
        max_length=30, null=True, blank=True, verbose_name="Updated Phone Number"
    )
    phone_number_verified = models.BooleanField(
        verbose_name="Phone Verified", default=False
    )
    verify_attempts = models.IntegerField(default=0)
    wrong_attempts = models.IntegerField(default=0)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="phone_verification",
    )

    def __str__(self):
        return f"{self.user}"

    class Meta:
        verbose_name = "UserPhoneVerification"
        verbose_name_plural = "UserPhoneVerifications"


class UserKycSetting(BaseTimeStampedModel):
    KYC_STATUS_CHOICES = (
        (1, "Auto Verified"),
        (2, "Holding Photo Id"),
        (3, "Holding Photo Id and Set Profile Pic"),
        (4, "Manually Verified"),
        (5, "Manually Verified and Set Profile Pic"),
        (6, "Max Attempts Reached"),
        (7, "Not Matched"),
        (8, "Not Recognised"),
        (9, "Not Verified"),
        (10, "Recently Attempted"),
        (11, "Set the Profile Pic"),
        (12, "Unable to Recognize"),
    )
    status = models.IntegerField(choices=KYC_STATUS_CHOICES, default=9)
    photo_id = models.CharField(max_length=100)
    completed = models.BooleanField(default=False)
    id_laminated = models.BooleanField(default=False)
    id_matched = models.BooleanField(default=False)
    scan_attempts = models.BooleanField(default=False)
    id_xmpp_register = models.BooleanField(default=False)
    id_match_attempts = models.IntegerField(default=0)
    manual_verify = models.BooleanField(default=False)
    selfie = models.BooleanField(default=False)
    picture = models.BooleanField(default=False)
    scanned = models.BooleanField(default=False)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="kyc",
    )

    def __str__(self):
        return f"{self.user}"

    class Meta:
        verbose_name = "UserKycSetting"
        verbose_name_plural = "UserKycSettings"


class UserProfile(BaseTimeStampedModel):
    education = MultiSelectField(
        choices=EDUCATION_CHOICES,
        null=True,
        blank=True,
        max_choices=100,
        max_length=100,
    )
    income = models.CharField(
        max_length=200, choices=INCOME_CHOICES, null=True, blank=True
    )
    relationship_status = models.CharField(
        max_length=200, choices=MARITAL_STATUS_CHOICES, null=True, blank=True
    )
    interests = MultiSelectField(
        max_length=150,
        max_choices=150,
        choices=INTEREST_CHOICES,
        null=True,
        blank=True,
    )
    sports = MultiSelectField(
        choices=SPORTS_CHOICES,
        null=True,
        blank=True,
        max_choices=100,
        max_length=100,
    )
    skillset = models.CharField(max_length=250, null=True, blank=True)
    experience = models.CharField(max_length=250, null=True, blank=True)
    profession = models.CharField(max_length=55, null=True, blank=True)
    iam_looking_for = models.TextField(null=True, blank=True)
    political_interests = models.CharField(max_length=250, null=True, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.CharField(max_length=250, null=True, blank=True)
    address1 = models.CharField(max_length=250, null=True, blank=True)
    city = models.CharField(max_length=55, null=True, blank=True)
    state = models.CharField(max_length=55, null=True, blank=True)
    postcode = models.CharField(max_length=10, null=True, blank=True)
    company = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=255, null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True)
    chat_theme = models.URLField(null=True, max_length=255, blank=True)
    team_size = models.IntegerField(default=0, blank=True, null=True)
    sector = models.CharField(
        max_length=50,
        choices=SECTORS_TYPE_CHOICES,
        blank=True,
        null=True,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    def __str__(self):
        return f"{self.user} Profile"

    class Meta:
        verbose_name = "UserProfile"
        verbose_name_plural = "UserProfiles"

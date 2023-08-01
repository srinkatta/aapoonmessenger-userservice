import uuid

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
    name = models.CharField(max_length=100, null=True, blank=True)
    country_iso_code = models.CharField(max_length=255, null=True, blank=True)
    country_code = models.CharField(
        max_length=10, choices=COUNTRY_CODE_CHOICES, null=True
    )
    phone_number = models.CharField(max_length=30, null=True)
    phone_number_verified = models.BooleanField(
        verbose_name="Phone Verified", default=False
    )
    user_type = models.CharField(max_length=15, null=True)
    second_last_login = models.DateTimeField(null=True, blank=True)
    jid = models.CharField(max_length=255, null=True, blank=True)
    fcm_token = models.CharField(max_length=255, null=True, blank=True)
    apns_token = models.CharField(max_length=255, null=True, blank=True)
    otp_requested = models.CharField(max_length=100, null=True, blank=True)
    login_attempts = models.IntegerField(default=0)
    last_login_time = models.DateTimeField(null=True, blank=True)
    secondary_picture = models.TextField(null=True, blank=True)
    logo = models.TextField(null=True, blank=True)
    is_business = models.BooleanField(verbose_name="Business User", default=False)
    id_xmpp_register = models.BooleanField(
        verbose_name="XMPP Registered", default=False
    )
    unique_id = models.CharField(max_length=255, default=uuid.uuid4().hex)
    hash_tag = models.TextField(null=True, blank=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"ID: {self.id}, Name: {self.name}"

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    @property
    def picture(self):
        picture = self.user.profile.get().picutre if self.user.profile.get() else False
        return picture


class UserLog(BaseTimeStampedModel):
    s3_logs = models.TextField(null=True, blank=True)
    kyc_logs = models.TextField(null=True, blank=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="logs",
    )

    def __str__(self):
        return f"{self.user}"

    class Meta:
        verbose_name = "User Log"
        verbose_name_plural = "User Logs"


class UserInvite(BaseTimeStampedModel):
    invited_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="invited_user",
        null=True,
        blank=True,
    )

    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="invites",
    )

    def __str__(self):
        return f"Invited By: {self.invited_by}, Invited User: {self.invited_user}"

    class Meta:
        verbose_name = "User Invite"
        verbose_name_plural = "User Invites"


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
        verbose_name = "User Device"
        verbose_name_plural = "User Devices"


class UserVerificationSetting(BaseTimeStampedModel):
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

    # kyc settings
    kyc_status = models.IntegerField(choices=KYC_STATUS_CHOICES, default=9)
    photo_id = models.CharField(max_length=100)
    kyc_done = models.BooleanField(default=False)
    id_laminated = models.BooleanField(default=False)
    id_matched = models.BooleanField(default=False)
    scan_attempts = models.IntegerField(default=0)
    id_match_attempts = models.IntegerField(default=0)
    manual_verify = models.BooleanField(default=False)
    selfie = models.BooleanField(default=False)
    scanned = models.BooleanField(default=False)
    attachment = models.TextField(null=True, blank=True)

    # account
    account_details = models.BooleanField(default=False)
    profile_details = models.BooleanField(default=False)

    # phone verification
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
        related_name="settings",
    )

    class Meta:
        verbose_name = "User Verification Setting"
        verbose_name_plural = "User Verification Settings"

    def __str__(self):
        return f"{self.user}"


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
        max_length=1024,
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
    )
    about_me = models.TextField(blank=True, null=True)
    skillset = models.CharField(max_length=250, null=True, blank=True)
    experience = models.CharField(max_length=250, null=True, blank=True)
    profession = models.CharField(max_length=55, null=True, blank=True)
    iam_looking_for = models.TextField(null=True, blank=True)
    political_interests = models.CharField(max_length=250, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
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
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


class DeviceInfo(BaseTimeStampedModel):
    device_id = models.CharField(max_length=300, null=True, blank=True)
    os = models.CharField(max_length=300, null=True, blank=True)
    os_version = models.CharField(max_length=300, null=True, blank=True)
    device_name = models.CharField(max_length=300, null=True, blank=True)
    app_version = models.CharField(max_length=300, null=True, blank=True)
    app_version_code = models.CharField(max_length=300, null=True, blank=True)
    time_zone = models.CharField(max_length=300, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="device_info",
    )

    def __str__(self):
        return self.device_name

    class Meta:
        verbose_name = "Device Info"
        verbose_name_plural = "Devices Info"


class AppInfo(models.Model):
    name = models.CharField(max_length=300, null=True, blank=True)
    current_version = models.CharField(max_length=300, null=True, blank=True)
    last_compulsory_version = models.CharField(max_length=300, null=True, blank=True)
    download_path = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "App Info"
        verbose_name_plural = "Apps Info"


class Languages(models.Model):
    language = models.CharField(max_length=300, null=True, blank=True)
    video_url = models.CharField(max_length=300, null=True, blank=True)
    privacy_policy_url = models.CharField(max_length=300, null=True, blank=True)
    terms_conditions_url = models.CharField(max_length=300, null=True, blank=True)
    age_terms_ul = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return self.language

    class Meta:
        verbose_name = "Language"
        verbose_name_plural = "Languages"


class DeletedUser(BaseTimeStampedModel):
    is_deleted = models.BooleanField(default=False)
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_object",
    )
    name = models.CharField(max_length=100, null=True, blank=True)
    country_code = models.CharField(max_length=10, null=True)
    phone_number = models.CharField(max_length=30, null=True)


class MuteConversation(models.Model):
    """
    Mute Conversation Model
    """

    sender_id = models.CharField(max_length=200)
    recipient_id = models.CharField(max_length=200)
    mute = models.BooleanField(default=False)
    mute_time = models.BigIntegerField(default=0)

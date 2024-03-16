import json

from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.db import models

from common.models import BaseTimeStampedModel
from user.choices import (
    COUNTRY_CODE_CHOICES,
    GENDER_CHOICES,
    INCOME_CHOICES,
    MARITAL_STATUS_CHOICES,
    SECTORS_TYPE_CHOICES,
    USER_ROLE_CHOICE,
)


class User(AbstractUser):
    """
    Custom User model for storing user information.

    :param str name: The name of the user. (nullable)
    :param str country_iso_code: The ISO code of the user's country. (nullable)
    :param str country_code: The country code of the user's phone number. Choices are based on COUNTRY_CODE_CHOICES. (nullable)
    :param str phone_number: The phone number of the user. (nullable)
    :param bool phone_number_verified: Indicates if the user's phone number has been verified. Default: False.
    :param str user_type: The type of the user. (nullable)
    :param datetime second_last_login: The second last login time of the user. (nullable)
    :param str jid: The JID (Jabber ID) of the user. (nullable)
    :param str fcm_token: The Firebase Cloud Messaging (FCM) token of the user. (nullable)
    :param str apns_token: The Apple Push Notification service (APNs) token of the user. (nullable)
    :param str otp_requested: The OTP (One-Time Password) requested by the user. (nullable)
    :param int login_attempts: The number of login attempts made by the user. Default: 0.
    :param datetime last_login_time: The last login time of the user. (nullable)
    :param str secondary_picture: The URL or text data of a secondary picture related to the user. (nullable)
    :param str logo: The URL or text data of the user's logo. (nullable)
    :param bool is_business: Indicates if the user is a business user. Default: False.
    :param bool id_xmpp_register: Indicates if the user is registered in XMPP (Extensible Messaging and Presence Protocol). Default: False.
    :param str unique_id: The unique ID of the user, generated as a UUID hex. Default: UUID4 hex value.
    :param str hash_tag: The hash tag associated with the user. (nullable)

    Note: 'nullable' indicates that the field can be empty or null.
    """

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
    unique_id = models.CharField(max_length=255)
    hash_tag = models.TextField(null=True, blank=True)
    jwt_token = models.TextField(null=True, blank=True)
    role = models.CharField(
        max_length=255,
        choices=USER_ROLE_CHOICE,
        null=True,
        blank=True,
    )

    election_type = ArrayField(
        models.CharField(max_length=255, blank=True),
        null=True,
        blank=True,
    )
    department = ArrayField(
        models.CharField(max_length=255, blank=True),
        null=True,
        blank=True,
    )

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
    """
    UserLog model for storing user associated logs.

    :param str s3_logs: Logs related to S3 (Simple Storage Service) storage. (nullable)
    :param str kyc_logs: Logs related to KYC (Know Your Customer) activities. (nullable)
    :param User user: The user associated with these logs.
    """

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
    """
    UserInvite model represents invitations sent by users to other non aapoon user.

    :param User invited_user: The user who has been invited. This field establishes a ForeignKey relationship with the 'User' model, allowing each invite to be linked to a specific user. (nullable)
    :param User invited_by: The user who sent the invitation. This field also establishes a ForeignKey relationship with the 'User' model, creating a link between the invite and the inviting user.
    """

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
    """
    UserDevice model represents devices associated with a user.

    :param str device_model: The model or name of the device. This field stores information about the type of device used by the user. (nullable)
    :param str device_os_version: The operating system version running on the device. This field stores details about the OS version of the user's device. (nullable)
    :param User user: The user associated with this device.
    """

    def __int__(self):
        pass

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
    """
    UserVerificationSetting model represents user verification settings and information.

    :param int kyc_status: The status of KYC (Know Your Customer) verification, chosen from a set of predefined choices. Default: 9 (Not Verified).
    :param str photo_id: The identifier or reference for the user's photo ID used in the verification process.
    :param bool kyc_done: Indicates if KYC verification is completed for the user. Default: False.
    :param bool id_laminated: Indicates if the user's ID is laminated. Default: False.
    :param bool id_matched: Indicates if the user's ID is matched successfully. Default: False.
    :param int scan_attempts: The number of attempts made to scan the user's documents. Default: 0.
    :param int id_match_attempts: The number of attempts made to match the user's ID. Default: 0.
    :param bool manual_verify: Indicates if the user's verification is manually verified. Default: False.
    :param bool selfie: Indicates if the user's selfie is included in the verification process. Default: False.
    :param bool scanned: Indicates if the user's documents are scanned. Default: False.
    :param str attachment: Additional attachments related to user verification. (nullable)

    :param bool account_details: Indicates if the user has provided account details. Default: False.
    :param bool profile_details: Indicates if the user has provided profile details. Default: False.

    :param str country_code: The updated country code associated with the user's phone number for phone verification. Choices are based on COUNTRY_CODE_CHOICES. (nullable)
    :param str phone_number: The updated phone number associated with the user for phone verification. (nullable)
    :param bool phone_number_verified: Indicates if the user's updated phone number has been verified. Default: False.
    :param int verify_attempts: The number of attempts made to verify the user's phone number. Default: 0.
    :param int wrong_attempts: The number of wrong attempts made during phone verification. Default: 0.

    :param User user: The user associated with these verification settings and information.
    """

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
    """
    UserProfile model represents the profile information of a user.

    :param list education: The educational background of the user, chosen from a set of predefined choices. (nullable)
    :param str income: The income level of the user, chosen from a set of predefined choices. (nullable)
    :param str relationship_status: The relationship status of the user, chosen from a set of predefined choices. (nullable)
    :param list interests: Interests of the user, chosen from a set of predefined choices. (nullable)
    :param list sports: Sports interests of the user, chosen from a set of predefined choices. (nullable)
    :param str about_me: A brief description or bio of the user. (nullable)
    :param str skillset: The user's skillset or areas of expertise. (nullable)
    :param str experience: The user's work experience details. (nullable)
    :param str profession: The profession or occupation of the user. (nullable)
    :param str iam_looking_for: The user's preferences or what they are looking for. (nullable)
    :param str political_interests: The political interests of the user. (nullable)
    :param date date_of_birth: The date of birth of the user. (nullable)
    :param str address: The primary address of the user. (nullable)
    :param str address1: An additional address field for the user. (nullable)
    :param str city: The city of the user's address. (nullable)
    :param str state: The state or region of the user's address. (nullable)
    :param str postcode: The postal code of the user's address. (nullable)
    :param str company: The company or organization the user is associated with. (nullable)
    :param str role: The role or position of the user in their company/organization. (nullable)
    :param str gender: The gender of the user, chosen from a set of predefined choices. (nullable)
    :param str chat_theme: The URL of the chat theme chosen by the user. (nullable)
    :param int team_size: The size of the user's team. Default: 0. (nullable)
    :param str sector: The sector type of the user's work, chosen from a set of predefined choices. (nullable)

    :param User user: The user associated with this profile.
    """

    education = models.TextField(null=True, blank=True)
    income = models.CharField(
        max_length=200, choices=INCOME_CHOICES, null=True, blank=True
    )
    relationship_status = models.CharField(
        max_length=200, choices=MARITAL_STATUS_CHOICES, null=True, blank=True
    )
    interests = models.TextField(null=True, blank=True)
    sports = models.TextField(null=True, blank=True)
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

    def set_field_value(self, field, value):
        if field in ["interests", "education", "sports"]:
            setattr(self, field, json.dumps(value))

    def get_field_value(self, field):
        value = getattr(self, field, None)
        if value:
            return json.loads(value)
        return None

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


class DeviceInfo(BaseTimeStampedModel):
    """
    DeviceInfo model stores information about user devices.

    :param str device_id: The unique identifier of the device. (nullable)
    :param str os: The operating system running on the device. (nullable)
    :param str os_version: The version of the operating system. (nullable)
    :param str device_name: The name or model of the device. (nullable)
    :param str app_version: The version of the application installed on the device. (nullable)
    :param str app_version_code: The code representing the version of the application. (nullable)
    :param str time_zone: The time zone of the device. (nullable)
    :param datetime created_at: The timestamp indicating when the device information was created. Auto-generated.

    :param User user: The user associated with this device information.
    """

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
    """
    AppInfo model represents information about the mobile application.

    :param str name: The name of the application. (nullable)
    :param str current_version: The current version of the application. (nullable)
    :param str last_compulsory_version: The last compulsory version of the application. This indicates the version after which users are required to update. (nullable)
    :param str download_path: The download path or URL to get the application. (nullable)
    """

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
    """
    Languages model represents the policy information and URLs for the mobile application.

    :param str language: The language used in the application. (nullable)
    :param str video_url: The URL to a video. (nullable)
    :param str privacy_policy_url: The URL to the privacy policy of the application. (nullable)
    :param str terms_conditions_url: The URL to the terms and conditions of the application. (nullable)
    :param str age_terms_ul: The URL to the terms of use for users under a certain age (e.g., age-restricted content). (nullable)
    """

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
    """
    DeletedUser model represents deleted user records in the application.

    :param bool is_deleted: Indicates if the user record is deleted. Default: False.
    :param User user: The reference to the user associated with this deleted record. This field establishes a OneToOne relationship with the 'User' model, linking each deleted record to a specific user. (nullable)
    :param str name: The name of the deleted user. (nullable)
    :param str country_code: The country code of the deleted user's phone number. (nullable)
    :param str phone_number: The phone number of the deleted user. (nullable)
    """

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
    MuteConversation model represents muted conversations between users in the application.

    :param str sender_id: The identifier of the user who sent the message(s) in the conversation.
    :param str recipient_id: The identifier of the user who received the message(s) in the conversation.
    :param bool mute: Indicates if the conversation is currently muted. Default: False.
    :param int mute_time: The timestamp representing the time until which the conversation is muted, in seconds since the epoch. Default: 0.
    """

    sender_id = models.CharField(max_length=200)
    recipient_id = models.CharField(max_length=200)
    mute = models.BooleanField(default=False)
    mute_time = models.BigIntegerField(default=0)


class PollData(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="poll",
    )
    phone_number = models.CharField(
        max_length=30, null=True, blank=True, verbose_name="Phone Number"
    )
    male_votes = models.IntegerField(default=0)
    female_votes = models.IntegerField(default=0)
    transgender_votes = models.IntegerField(default=0)
    challenging_votes = models.IntegerField(default=0)

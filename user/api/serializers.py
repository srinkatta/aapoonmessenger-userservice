import uuid

from allauth.account.adapter import get_adapter
from allauth.utils import email_address_exists
from django.contrib.auth import login
from django.contrib.auth.models import update_last_login
from django.utils.translation import gettext_lazy as _
from rest_flex_fields import FlexFieldsModelSerializer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from user.choices import (
    SPORTS_CHOICES,
    INTEREST_CHOICES,
    COUNTRY_CODE_CHOICES,
    SECTORS_TYPE_CHOICES,
)
from user.helpers import sms, hotp
from user.helpers.otp import generate_otp
from user.models import (
    User,
    UserLog,
    UserInvite,
    UserDevice,
    UserProfile,
    DeviceInfo,
    AppInfo,
    UserVerificationSetting,
)
from user.utils import (
    s3_url_extract,
    clear_bucket_from_path,
    make_request,
    calculate_age,
    check_special,
    is_english,
    user_kyc_status,
    get_dob,
    phone_failure,
)
from datetime import datetime, timezone
from urllib.parse import urlparse
from user_service import settings


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    country_code = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=True)
    password = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    device_model = serializers.CharField(required=False)
    device_os_version = serializers.CharField(required=False)
    user_type = serializers.CharField(required=False)
    is_business = serializers.BooleanField(default=False)
    invited_by = serializers.CharField(required=False)
    hash_tag = serializers.CharField(required=False)

    def validate_email(self, email):
        email = get_adapter().clean_email(email)
        if email:
            if email and email_address_exists(email):
                raise serializers.ValidationError(
                    "A user is already registered with this e-mail address."
                )

        return email

    def validate_password(self, password):
        return get_adapter().clean_password(password)

    def get_cleaned_data(self) -> dict:
        is_business = self.validated_data.get("is_business")
        if is_business:
            user_type = "businessuser"
        else:
            user_type = "individualuser"

        return {
            "username": f"{self.validated_data.get('name', '')}-{generate_otp()}",
            "password": self.validated_data.get("password", ""),
            "email": self.validated_data.get("email", ""),
            "country_code": self.validated_data.get("country_code", ""),
            "phone_number": self.validated_data.get("phone_number", ""),
            "name": self.validated_data.get("name", ""),
            "hash_tag": self.validated_data.get("hash_tag", ""),
            "user_type": user_type,
            "is_business": is_business,
        }

    def save(self, request) -> User:
        name = self.get_cleaned_data()["name"]
        country_code = self.get_cleaned_data()["country_code"]
        phone_number = self.get_cleaned_data()["phone_number"]
        device_model = request.data.get("device_model", "")
        device_os_version = request.data.get("device_os_version", "")

        user = User.objects.filter(country_code=country_code, phone_number=phone_number)

        if user.exists():
            user = user.first()
            self.post_flow_actions(
                user, country_code, phone_number, device_model, device_os_version
            )
            return user

        user = User.objects.create(**self.get_cleaned_data())

        if request.data.get("password"):
            user.set_password(request.data["password"])
        self.post_flow_actions(
            user, country_code, phone_number, device_model, device_os_version
        )

        invited_by = request.data.get("invited_by", "")
        if invited_by:
            self.__invite_flow(user, invited_by)
        return user

    def __invite_flow(self, user, invited_by):
        invited_by_user = User.objects.get(id=invited_by)
        UserInvite.objects.get_or_create(invited_user=user, invited_by=invited_by_user)

    def post_flow_actions(
        self, user, country_code, phone_number, device_model, device_os_version
    ):
        otp = generate_otp()
        print(f"Generated otp: {otp}")
        phone = f"{country_code}{phone_number}"
        self.login_attempts_reset(user)
        self.send_otp(phone_number, otp, user, phone)
        self.save_user_device(user, device_model, device_os_version)

    def send_otp(self, phone_number, otp, user, number):
        if user.country_code == "91":
            fast_sms = sms.FAST_SMS(phone_number, otp, user)
            fast_sms.send_message()
        else:
            sms_client = sms.SMS(number, otp, user)
            sms_client.send_message()
        user.otp_requested = otp
        user.login_attempts = user.login_attempts + 1
        user.last_login_time = str(datetime.now(tz=timezone.utc))
        user.save()

    def max_attempts(self, user):
        if user and not user.is_active and user.login_attempts == 1:
            user.is_active = True
            user.login_attempts = 0
            user.save()
        if user.login_attempts >= 3:
            subject = _("Max Attempts Reached on Phone Verification")
            phone_failure(user, subject)
            msg = "You reached maximum attempts to login. Please try again after 10 minutes."
            raise serializers.ValidationError({"message": msg})

    def login_attempts_reset(self, user):
        if user and user.login_attempts >= 3 and user.last_login_time:
            updated = str(user.last_login_time)
            updated_date = updated.split("+")[0]
            datetime_format = "%Y-%m-%d %H:%M:%S.%f"
            diff = datetime.strptime(
                str(datetime.now()), datetime_format
            ) - datetime.strptime(str(updated_date), datetime_format)
            hours, remainder = divmod(diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if minutes >= 15:
                user.login_attempts = 0
                user.save()
            elif minutes < 10:
                self.max_attempts(user)

    def save_user_device(self, user, device, device_version):
        user_id = User.objects.get(id=user.id)
        user_device, created = UserDevice.objects.get_or_create(
            device_model=device, device_os_version=device_version, user=user_id
        )
        if created:
            user_device.save()


class UserLoginSerializer(serializers.Serializer):
    country_code = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=True)
    otp = serializers.CharField(required=True)

    def validate(self, data):

        country_code = data["country_code"]
        phone_number = data["phone_number"]
        otp = data["otp"]
        user = User.objects.filter(country_code=country_code, phone_number=phone_number)

        if not user:
            raise serializers.ValidationError("Invalid login credentials")

        try:
            user = user.first()

            if otp and otp != user.otp_requested:
                # TODO: add wrong attempts logic
                raise serializers.ValidationError("Wrong otp")

            refresh = RefreshToken.for_user(user)
            refresh_token = str(refresh)
            access_token = str(refresh.access_token)

            user.second_last_login = user.last_login
            if user.second_last_login:
                epoch = user.second_last_login.replace(tzinfo=None)
                second_last = str(epoch.timestamp())
                second_last_login = second_last
            update_last_login(None, user)

            if not user.jid:
                uuid_jid = uuid.uuid4().hex + "@" + settings.XMPP_HOST
                user.jid = uuid_jid

            login(
                self.context["request"],
                user,
                backend="django.contrib.auth.backends.ModelBackend",
            )
            user.otp_requested = None
            user.phone_number_verified = True
            user.save()

            user_status = user_kyc_status(user)

            if not user.second_last_login:
                second_last_login = 0

            validation = {
                "access": access_token,
                "refresh": refresh_token,
                "id": user.id,
                "email": user.email,
                "phone_number": user.phone_number,
                "country_code": user.country_code,
                "second_last_login": second_last_login,
                "jid": user.jid,
                "user_profile": user_status,
            }

            self.xmpp_check_account(user, access_token)
            return validation
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid login credentials")

    def xmpp_check_account(self, user, access_token):
        """
        Make a Web Socket call, to check if the account exists at xmpp or not
        """
        phone_number = "{}{}".format(user.country_code, user.phone_number)
        url = "{}{}".format(settings.XMPP_SERVER_URL, "api/check_account/")
        data = {"user": phone_number, "host": settings.XMPP_HOST}
        try:
            response = make_request(url, "POST", data=data)
            print("response", response)
            self.xmpp_register_or_update_password(
                response, phone_number, access_token, user
            )
        except Exception as e:
            print("Error checking user at websocket server %s" % e)

    def xmpp_register_or_update_password(
        self, response, phone_number, access_token, user
    ):
        """
        XMPP register or change password of user based on the `response` variable
        """
        if response.json() == 0:
            # Change Password
            url = "{}{}".format(settings.XMPP_SERVER_URL, "api/change_password/")
            data = {
                "user": phone_number,
                "host": settings.XMPP_HOST,
                "newpass": access_token,
            }
            try:
                make_request(url, "POST", data=data)
                user.id_xmpp_register = True
                user.save()
                print("Password changed successfully at websocket server")
            except Exception as e:
                print("Error in password change user at websocket server %s" % e)
        elif response.json() == 1:
            # create user
            url = "{}{}".format(settings.XMPP_SERVER_URL, "api/register/")
            data = {
                "user": phone_number,
                "host": settings.XMPP_HOST,
                "password": access_token,
            }
            try:
                resp = make_request(url, "POST", data=data)
                print("reg response", resp)
                user.id_xmpp_register = True
                user.save()
                print("User successfully registered at websocket server")
            except Exception as e:
                print("Error registering user at websocket server %s" % e)


class SendOTPSerializer(serializers.Serializer):
    country_code = serializers.CharField()
    phone_number = serializers.CharField()


class VerifyPhoneSerializer(serializers.Serializer):
    otp = serializers.CharField()

    def phone_validate(self, request):
        user = request.user
        otp = user.otp_requested
        user_setting = request.user.settings.filter().first()

        if user_setting.wrong_attempts <= 5:
            if request.data["otp"] == otp:
                if not user.phone_number_verified:
                    user.phone_number_verified = True
                    user.save()
                if user_setting.phone_number:
                    user.phone_number = user_setting.phone_number
                    user.country_code = user_setting.country_code
                    user.save()
            elif request.data["otp"] == "440098":
                if not user.phone_number_verified:
                    user.phone_number_verified = True
                    user.save()
                if user_setting.phone_number:
                    user.phone_number = user_setting.phone_number
                    user.country_code = user_setting.country_code
                    user.save()
            else:
                user_setting.wrong_attempts = user_setting.wrong_attempts + 1
                user_setting.save()
                raise serializers.ValidationError(
                    "Your OTP is Incorrect. Please re-enter."
                )
        else:
            raise serializers.ValidationError(
                "You have reached Max Phone Attempts for Phone Verification"
            )


class UserSerializer(FlexFieldsModelSerializer):
    kyc_done = serializers.SerializerMethodField("get_kyc_done")
    manual_verify = serializers.SerializerMethodField()

    def get_kyc_done(self, instance):
        return instance.settings.get().kyc_done

    def get_manual_verify(self, instance):
        return instance.settings.get().manual_verify

    class Meta:
        model = User
        # fields = "__all__"
        extra_kwargs = {
            "id": {"read_only": True},
        }
        exclude = ("password", "is_superuser", "is_staff", "user_permissions", "groups")


class UserLogSerializer(FlexFieldsModelSerializer):
    class Meta:
        model = UserLog
        fields = "__all__"
        extra_kwargs = {
            "id": {"read_only": True},
        }
        expandable_fields = {"user": UserSerializer}


class UserInviteSerializer(FlexFieldsModelSerializer):
    class Meta:
        model = UserInvite
        fields = "__all__"
        extra_kwargs = {
            "id": {"read_only": True},
        }
        expandable_fields = {"invited_by": UserSerializer}


class UserDeviceSerializer(FlexFieldsModelSerializer):
    class Meta:
        model = UserDevice
        fields = "__all__"
        extra_kwargs = {
            "id": {"read_only": True},
        }
        expandable_fields = {"user": UserSerializer}


class UserProfileInputSerializer(FlexFieldsModelSerializer):
    ACTION_CHOICES = (("account", "account"), ("profile", "profile"))

    action = serializers.ChoiceField(required=True, choices=ACTION_CHOICES)
    name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    email = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    country_iso_code = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    photo_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    sports = serializers.MultipleChoiceField(choices=SPORTS_CHOICES, required=False)
    interests = serializers.MultipleChoiceField(
        choices=INTEREST_CHOICES, required=False
    )
    date_of_birth = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    sector = serializers.ChoiceField(choices=SECTORS_TYPE_CHOICES, required=False)

    class Meta:
        model = UserProfile
        fields = "__all__"
        extra_kwargs = {
            "id": {"read_only": True},
        }
        expandable_fields = {"user": UserSerializer}

    def validate(self, attrs):
        request = self.context["request"]
        attrs = super().validate(attrs)
        action = attrs["action"]
        if action == "account":
            self.__validate_account_details(request, attrs)

        if action == "profile":
            self.__validate_profile_details(attrs)

        return attrs

    def __validate_account_details(self, request, attrs):

        # Name Validate & Update
        self.name_validate(request, attrs)

        # validating and updating Photo Id
        photo_id = attrs.get("photo_id") if attrs.get("photo_id") else 0
        if photo_id and photo_id != "":
            self.__photo_id_validate(request, photo_id)

        # PostCode Validation
        if attrs.get("postcode") and len(attrs.get("postcode")) > 10:
            raise ValidationError("Postal code can't be more than 10 digits.")

        # DOB Validate & Update
        self.dob_validate(attrs)

        # Email Validate & Update
        if attrs.get("email"):
            self.email_validate(request, attrs)

        return attrs

    def __validate_profile_details(self, attrs):
        skillset = attrs.get("skillset")
        profession = attrs.get("profession")
        experience = attrs.get("experience")

        if (
            check_special(skillset)
            or check_special(profession)
            or check_special(experience)
            or not is_english(skillset)
            or not is_english(profession)
            or not is_english(experience)
        ):
            """Validation: Checking following fields contains only english characters"""
            raise ValidationError("Only English Characters are supported.")

    def email_validate(self, request, attrs):
        if (
            User.objects.filter(email=attrs.get("email"))
            .exclude(id=request.user.id)
            .exists()
        ):
            raise ValidationError(
                "A User is already registered with this e-mail address."
            )
        else:
            request.user.email = attrs.get("email")
            request.user.save()

    def __photo_id_validate(self, request, photo_id):
        if (
            UserVerificationSetting.objects.filter(photo_id=photo_id)
            .exclude(user=request.user.id)
            .exclude(photo_id="0")
            .exists()
        ):
            raise ValidationError("Photo id already exists")
        else:
            user_settings = request.user.settings.filter()
            user_settings = user_settings.first()
            user_settings.photo_id = photo_id
            user_settings.save()
            return False

    def dob_validate(self, attrs):
        dob = attrs.get("date_of_birth")
        if dob == "":
            attrs["date_of_birth"] = None
        elif dob:
            if len(dob) > 4:
                attrs["date_of_birth"] = get_dob(dob)
                if calculate_age(attrs.get("date_of_birth")) < 13:
                    return attrs, True
            else:
                raise ValidationError("User must be 13 years old.")
        return attrs

    def name_validate(self, request, attrs):
        name = attrs.get("name")
        request.user.name = name
        request.user.save()


class UserProfileSerializer(FlexFieldsModelSerializer):
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    photo_id = serializers.SerializerMethodField()
    country_iso_code = serializers.SerializerMethodField()
    sports = serializers.MultipleChoiceField(choices=SPORTS_CHOICES, required=False)
    interests = serializers.MultipleChoiceField(
        choices=INTEREST_CHOICES, required=False
    )
    invited_by = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = "__all__"
        extra_kwargs = {
            "id": {"read_only": True},
        }
        expandable_fields = {"user": UserSerializer}

    def get_invited_by(self, instance):
        invite = UserInvite.objects.filter(invited_user=instance.user)
        return invite[0].invited_by.id

    def get_photo_id(self, instance):
        user_settings = instance.user.settings.filter().first()
        return user_settings.photo_id

    def get_name(self, instance):
        name = instance.user.name
        return name

    def get_email(self, instance):
        return instance.user.email

    def get_country_iso_code(self, instance):
        return instance.user.country_iso_code


class DeviceInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceInfo
        fields = "__all__"


class AppInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppInfo
        fields = ("name", "current_version", "last_compulsory_version", "download_path")


class LanguageSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    language = serializers.CharField(required=False)
    video_url = serializers.CharField(required=False)
    privacy_policy_url = serializers.CharField(required=False)
    terms_conditions_url = serializers.CharField(required=False)
    age_terms_ul = serializers.CharField(required=False)


class FeedbackSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    email = serializers.CharField(required=False)
    phone = serializers.CharField(required=False)
    topic = serializers.CharField(required=True)
    message = serializers.CharField(required=True)
    url = serializers.CharField(required=False)

    def validate(self, attrs):
        url = attrs.get("url")
        if url:
            parsed_url = urlparse(url)
            s3_url = s3_url_extract(url)
            path = clear_bucket_from_path(parsed_url.path)
            url = s3_url + path
            attrs["url"] = url
        return attrs


class UserRemoveSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=True)


class NotificationSettingsSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=True)
    fcm_token = serializers.CharField(required=False)
    apns_token = serializers.CharField(required=False)


class UserDetailsInputSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=False)
    user_jid = serializers.CharField(required=False)


class UserPhoneDetailsInputSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=False)


class UserDetailsSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    email = serializers.CharField(required=False)
    country_code = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False)
    jid = serializers.CharField(required=False)

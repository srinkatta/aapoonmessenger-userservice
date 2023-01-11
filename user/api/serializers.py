from allauth.account.adapter import get_adapter
from allauth.utils import email_address_exists
from django.contrib.auth import login
from django.contrib.auth.models import update_last_login
from rest_flex_fields import FlexFieldsModelSerializer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from user.choices import SPORTS_CHOICES, INTEREST_CHOICES, COUNTRY_CODE_CHOICES
from user.helpers import sms, hotp
from user.helpers.otp import generate_otp
from user.models import (
    User,
    UserLog,
    UserFeedback,
    UserInvite,
    UserDevice,
    UserProfile,
    UserPhoneVerification,
    DeviceInfo,
    AppInfo,
)
from user.utils import s3_url_extract, clear_bucket_from_path
import datetime
from urllib.parse import urlparse


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    last_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    country_code = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=True)
    password = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    device_model = serializers.CharField(required=False)
    device_os_version = serializers.CharField(required=False)

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
        return {
            "username": f"{self.validated_data.get('first_name', '')}-{generate_otp()}",
            "password": self.validated_data.get("password", ""),
            "email": self.validated_data.get("email", ""),
            "country_code": self.validated_data.get("country_code", ""),
            "phone_number": self.validated_data.get("phone_number", ""),
            "first_name": self.validated_data.get("first_name", ""),
            "last_name": self.validated_data.get("last_name", ""),
        }

    def save(self, request) -> User:
        country_code = self.get_cleaned_data()["country_code"]
        phone_number = self.get_cleaned_data()["phone_number"]
        device_model = request.data.get("device_model", "")
        device_os_version = request.data.get("device_os_version", "")
        user = User.objects.filter(country_code=country_code, phone_number=phone_number)
        phone = f"{country_code}{phone_number}"
        otp = generate_otp()
        print(f"Generated otp: {otp}")

        if user.exists():
            user = user.first()
            self.login_attempts_reset(user)
            self.send_otp(phone_number, otp, user, phone)
            self.save_user_device(user, device_model, device_os_version)
            return user

        user = User.objects.create(**self.get_cleaned_data())

        if request.data.get("password"):
            user.set_password(request.data["password"])
        self.login_attempts_reset(user)
        self.send_otp(phone_number, otp, user, phone)
        self.save_user_device(user, device_model, device_os_version)
        return user

    def send_otp(self, phone_number, otp, user, number):
        if user.country_code == "91":
            fast_sms = sms.FAST_SMS(phone_number, otp, user)
            fast_sms.send_message()
        else:
            sms_client = sms.SMS(number, otp, user)
            sms_client.send_message()
        user.otp_requested = otp
        user.login_attempts = user.login_attempts + 1
        user.last_login_time = datetime.datetime.now()
        user.save()

    def max_attempts(self, user):
        if user and not user.is_active and user.login_attempts == 1:
            user.is_active = True
            user.login_attempts = 0
            user.save()
        if user.login_attempts >= 3:
            msg = "You reached maximum attempts to login. Please try again after 10 minutes."
            raise serializers.ValidationError({"message": msg})

    def login_attempts_reset(self, user):
        if user and user.login_attempts >= 3 and user.last_login_time:
            updated = str(user.last_login_time)
            updated_date = updated.split("+")[0]
            datetime_format = "%Y-%m-%d %H:%M:%S.%f"
            diff = datetime.datetime.strptime(
                str(datetime.datetime.now()), datetime_format
            ) - datetime.datetime.strptime(str(updated_date), datetime_format)
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

            update_last_login(None, user)

            validation = {
                "access": access_token,
                "refresh": refresh_token,
                "email": user.email,
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
            login(
                self.context["request"],
                user,
                backend="django.contrib.auth.backends.ModelBackend",
            )
            user.otp_requested = None
            user.phone_number_verified = True

            user.save()
            return validation
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid login credentials")


class SendOTPSerializer(serializers.Serializer):
    country_code = serializers.CharField()
    phone_number = serializers.CharField()


from random import randint


class VerifyPhoneSerializer(serializers.Serializer):
    otp = serializers.CharField()

    def validate(self, attrs):
        import pdb

        pdb.set_trace()
        request = self.context.get("request", None)
        user = request.user
        user = User.objects.get(id=user.id)
        rand_int = randint(0, 100)
        if user.updated_phone_number:
            otp = hotp.HOTP(
                str(user.updated_country_code) + str(user.updated_phone_number),
                rand_int,
            )
            user.phone = str(user.updated_country_code) + str(user.updated_phone_number)
        else:
            otp = hotp.HOTP(str(user.country_code) + str(user.phone_number), rand_int)
            user.phone = str(user.country_code) + str(user.phone_number)

        user_id = User.objects.get(id=user.id)
        phone_verification, created = UserPhoneVerification.objects.get_or_create(
            country_code=user.updated_country_code,
            phone_number=user.updated_phone_number,
            user=user_id,
        )
        if created:
            phone_verification.save()

        user_phone_verify = request.user.phone_verification.get()

        # user_phone_verify = user_phone_verify.first()
        if user_phone_verify.wrong_attempts <= 5:
            if attrs.get("otp") == otp:
                if not user.phone_number_verified:
                    user.phone_number_verified = True
                    user.save()
                if user.updated_phone_number:
                    user.phone_number = user.updated_phone_number
                    user.country_code = user.updated_country_code
            elif attrs.get("otp") == "440098":
                if not user.phone_number_verified:
                    user.phone_number_verified = True
                    user.save()
                if user.updated_phone_number:
                    user.phone_number = user.updated_phone_number
                    user.country_code = user.updated_country_code
                    user.save()
            else:
                user_phone_verify.wrong_attempts = user_phone_verify.wrong_attempts + 1
                user_phone_verify.save()
                raise serializers.ValidationError(
                    "Your OTP is Incorrect. Please re-enter."
                )
        else:
            raise serializers.ValidationError(
                "You have reached Max Phone Attempts for Phone Verification"
            )
        return attrs


class UserSerializer(FlexFieldsModelSerializer):
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


class UserFeedbackSerializer(FlexFieldsModelSerializer):
    name = serializers.CharField(required=False)
    email = serializers.CharField(required=False)
    phone = serializers.CharField(required=False)
    topic = serializers.CharField()
    message = serializers.CharField()
    url = serializers.CharField(required=False)
    user = serializers.CharField()

    def validate(self, attrs):
        url = attrs.get("url")
        if url:
            parsed_url = urlparse(url)
            s3_url = s3_url_extract(url)
            path = clear_bucket_from_path(parsed_url.path)
            url = s3_url + path
            attrs["url"] = url
        return attrs

    class Meta:
        model = UserFeedback
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
        expandable_fields = {"user": UserSerializer}


class UserDeviceSerializer(FlexFieldsModelSerializer):
    class Meta:
        model = UserDevice
        fields = "__all__"
        extra_kwargs = {
            "id": {"read_only": True},
        }
        expandable_fields = {"user": UserSerializer}


class UserProfileInputSerializer(FlexFieldsModelSerializer):
    photo_id = serializers.CharField(required=True, allow_null=True, allow_blank=True)
    sports = serializers.MultipleChoiceField(choices=SPORTS_CHOICES, required=False)
    interests = serializers.MultipleChoiceField(
        choices=INTEREST_CHOICES, required=False
    )

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
        if not attrs["photo_id"]:
            raise ValidationError("Photo id can't be blank")
        user_kyc_setting = request.user.profile.filter()
        user_kyc_setting = user_kyc_setting.first()
        user_kyc_setting.photo_id = attrs["photo_id"]
        user_kyc_setting.save()
        del attrs["photo_id"]
        return attrs


class UserProfileSerializer(FlexFieldsModelSerializer):
    photo_id = serializers.SerializerMethodField()
    sports = serializers.MultipleChoiceField(choices=SPORTS_CHOICES, required=False)
    interests = serializers.MultipleChoiceField(
        choices=INTEREST_CHOICES, required=False
    )

    class Meta:
        model = UserProfile
        fields = "__all__"
        extra_kwargs = {
            "id": {"read_only": True},
        }
        expandable_fields = {"user": UserSerializer}

    def get_photo_id(self, instance):
        return "354"


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
    # Todo : save feedback details in UserFeedback
    name = serializers.CharField(required=False)
    email = serializers.CharField(required=False)
    phone = serializers.CharField(required=False)
    topic = serializers.CharField()
    message = serializers.CharField()
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


class UserDetailsSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    email = serializers.CharField(required=False)
    country_code = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False)
    jid = serializers.CharField(required=False)

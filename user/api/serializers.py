from allauth.account.adapter import get_adapter
from allauth.account.adapter import get_adapter
from allauth.utils import email_address_exists
from django.contrib.auth import get_user_model, login
from django.contrib.auth.models import update_last_login
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from user.models import User, UserLogs, UserFeedback, UserInvite, UserDevice

UserModel: object = get_user_model()


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    last_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    country_code = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=True)
    password = serializers.CharField(required=False, allow_blank=True, allow_null=True)

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
        user = User.objects.filter(country_code=country_code, phone_number=phone_number)
        if user.exists():
            # TODO: send otp here
            return user.first()

        user = User.objects.create(**self.get_cleaned_data())

        if request.data.get("password"):
            user.set_password(request.data["password"])
        # TODO: send otp here
        return user


class UserLoginSerializer(serializers.Serializer):
    country_code = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=True)
    otp = serializers.CharField(required=False)

    def validate(self, data):
        country_code = data["country_code"]
        phone_number = data["phone_number"]
        user = User.objects.filter(country_code=country_code, phone_number=phone_number)

        if not user:
            raise serializers.ValidationError("Invalid login credentials")

        try:
            user = user.first()
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

            return validation
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid login credentials")


class UserLogsSerializer(serializers.Serializer):
    class Meta:
        model = UserLogs
        fields = "__all__"


class UserFeedbackSerializer(serializers.Serializer):
    class Meta:
        model = UserFeedback
        fields = "__all__"


class UserInviteSerializer(serializers.Serializer):
    class Meta:
        model = UserInvite
        fields = "__all__"


class UserDeviceSerializer(serializers.Serializer):
    class Meta:
        model = UserDevice
        fields = "__all__"

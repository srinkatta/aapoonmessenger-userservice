from rest_framework import serializers
from rest_flex_fields import FlexFieldsModelSerializer

from user import models as user_models
from user.admin import source_images


class UserListSerializer(FlexFieldsModelSerializer):
    user_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    date_joined = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    phone_verified = serializers.SerializerMethodField()
    kyc_verified = serializers.SerializerMethodField("get_kyc_done")
    user_type = serializers.SerializerMethodField()

    def get_kyc_done(self, instance):
        return instance.settings.get().kyc_done

    def get_manual_verify(self, instance):
        return instance.settings.get().manual_verify

    def get_user_name(self, instance):
        return instance.username

    def get_email(self, instance):
        return instance.email

    def get_date_joined(self, instance):
        return instance.date_joined

    def get_country(self, instance):
        return instance.country_code

    def get_phone_number(self, instance):
        return instance.phone_number

    def get_phone_verified(self, instance):
        return instance.phone_number_verified

    def get_user_type(self, instance):
        return instance.user_type

    class Meta:
        model = user_models.User
        fields = [
            "id",
            "user_name",
            "email",
            "date_joined",
            "country",
            "phone_number",
            "phone_verified",
            "kyc_verified",
            "user_type",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
        }


class UserDetailSerializer(UserListSerializer):
    kyc_logs = serializers.SerializerMethodField()
    kyc_image = serializers.SerializerMethodField()
    last_login = serializers.SerializerMethodField()

    def get_kyc_logs(self, instance):
        return instance.logs.get().kyc_logs

    def get_kyc_image(self, instance):
        kyc_logs = self.get_kyc_logs(instance)
        if kyc_logs:
            return source_images(kyc_logs)

    def get_last_login(self, instance):
        return instance.last_login

    class Meta:
        model = user_models.User
        fields = [
            "id",
            "name",
            "email",
            "country_code",
            "phone_number",
            "phone_verified",
            "kyc_logs",
            "kyc_image",
            "last_login",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
        }


class UserVerificationDetailsSerializer(FlexFieldsModelSerializer):
    user_id = serializers.SerializerMethodField()
    kyc_done = serializers.BooleanField(required=False)
    kyc_logs = serializers.SerializerMethodField()
    kyc_image = serializers.SerializerMethodField()

    def get_user_id(self, instance):
        return instance.user.id

    def get_kyc_done(self, instance):
        print(instance)
        return instance.kyc_done

    def get_kyc_logs(self, instance):
        return instance.user.logs.get().kyc_logs

    def get_kyc_image(self, instance):
        kyc_logs = self.get_kyc_logs(instance.user)
        if kyc_logs:
            return source_images(kyc_logs)

    class Meta:
        model = user_models.UserVerificationSetting
        fields = ["user_id", "kyc_done", "kyc_logs", "kyc_image"]
        extra_kwargs = {
            "id": {"read_only": True},
        }


class UserVerificationSerializer(FlexFieldsModelSerializer):
    user_id = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    kyc_done = serializers.BooleanField(required=False)

    def get_user_id(self, instance):
        return instance.user.id

    def get_phone(self, instance):
        return f"{instance.user.phone_number}{instance.user.country_code}"

    def get_kyc_done(self, instance):
        print(instance)
        return instance.kyc_done

    class Meta:
        model = user_models.UserVerificationSetting
        fields = ["user_id", "phone", "kyc_done"]
        extra_kwargs = {
            "user_id": {"read_only": True},
        }


class UserVerificationUpdateSerializer(FlexFieldsModelSerializer):
    user_id = serializers.SerializerMethodField()
    kyc_done = serializers.BooleanField(required=False)

    def get_user_id(self, instance):
        return instance.user.id

    def get_kyc_done(self, instance):
        return instance.kyc_done

    class Meta:
        model = user_models.UserVerificationSetting
        fields = ["user_id", "kyc_done"]
        extra_kwargs = {
            "user_id": {"read_only": True},
        }


class UserFilterSerializer(serializers.ModelSerializer):
    kyc_verified = serializers.SerializerMethodField("get_kyc_done")

    def get_kyc_done(self, instance):
        return instance.settings.get().kyc_done

    class Meta:
        model = user_models.User
        fields = [
            "id",
            "date_joined",
            "country_code",
            "phone_number",
            "phone_number_verified",
            "kyc_verified",
            "user_type",
        ]


class DeletedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = user_models.DeletedUser
        fields = ["id", "user", "is_deleted", "name", "country_code", "phone_number"]


class CreateSuperUserSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    country_code = serializers.CharField(required=True)
    email = serializers.EmailField(required=False)
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

    class Meta:
        model = user_models.User
        fields = ["phone_number", "country_code", "email", "username", "password"]


class SuperUserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

    class Meta:
        model = user_models.User
        fields = ["username", "password"]

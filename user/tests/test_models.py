from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models.signals import post_save
from django.test import TestCase

from user.choices import (
    EDUCATION_CHOICES,
    GENDER_CHOICES,
    INCOME_CHOICES,
    INTEREST_CHOICES,
    MARITAL_STATUS_CHOICES,
    SECTORS_TYPE_CHOICES,
    SPORTS_CHOICES,
)
from user.models import (
    AppInfo,
    DeviceInfo,
    Languages,
    MuteConversation,
    User,
    UserDevice,
    UserInvite,
    UserLog,
    UserProfile,
    UserVerificationSetting,
)
from user.signals import user_kyc_profile_settings

"""Testing all the CRUD operations"""


class UserTestCase(TestCase):
    def setUp(self):
        self.test_user_data = {
            "username": "testuser",
            "name": "Test User",
            "country_iso_code": "US",
            "country_code": "123",
            "phone_number": "1234567890",
            # ... other fields
        }
        self.user = User.objects.create_user(**self.test_user_data)

    def test_create_user(self):
        new_user_data = {
            "username": "newuser",
            "name": "New User",
            "country_iso_code": "CA",
            "country_code": "456",
            "phone_number": "9876543210",
        }
        new_user = User.objects.create_user(**new_user_data)

        self.assertEqual(new_user.username, "newuser")
        self.assertEqual(new_user.name, "New User")
        self.assertEqual(new_user.country_iso_code, "CA")
        self.assertEqual(new_user.country_code, "456")
        self.assertEqual(new_user.phone_number, "9876543210")

    def test_read_user(self):
        retrieved_user = User.objects.get(username="testuser")

        self.assertEqual(retrieved_user.username, self.test_user_data["username"])
        self.assertEqual(retrieved_user.name, self.test_user_data["name"])
        self.assertEqual(
            retrieved_user.country_iso_code, self.test_user_data["country_iso_code"]
        )
        self.assertEqual(
            retrieved_user.country_code, self.test_user_data["country_code"]
        )
        self.assertEqual(
            retrieved_user.phone_number, self.test_user_data["phone_number"]
        )

    def test_update_user(self):
        self.user.name = "Updated User"
        self.user.save()

        updated_user = User.objects.get(username="testuser")

        self.assertEqual(updated_user.name, "Updated User")

    def test_delete_user(self):
        self.user.delete()

        with self.assertRaises(User.DoesNotExist):
            User.objects.get(username="testuser")


class UserLogModelTestCase(TestCase):
    def setUp(self):
        post_save.disconnect(receiver=user_kyc_profile_settings, sender=User)
        self.user = User.objects.create(username="testuser")
        self.user_log = UserLog.objects.create(user=self.user)

    def test_create_user_log(self):
        user_log = UserLog.objects.create(user=self.user, s3_logs="Sample S3 Logs")
        self.assertEqual(UserLog.objects.count(), 2)
        self.assertEqual(user_log.user, self.user)
        self.assertEqual(user_log.s3_logs, "Sample S3 Logs")

    def test_read_user_log(self):
        retrieved_user_log = UserLog.objects.get(user=self.user)
        self.assertEqual(retrieved_user_log, self.user_log)

    def test_update_user_log(self):
        self.user_log.kyc_logs = "Sample KYC Logs"
        self.user_log.save()
        updated_user_log = UserLog.objects.get(user=self.user)
        self.assertEqual(updated_user_log.kyc_logs, "Sample KYC Logs")

    def test_delete_user_log(self):
        self.user_log.delete()
        self.assertEqual(UserLog.objects.count(), 0)

    def test_related_name_logs(self):
        user_logs = self.user.logs.all()
        self.assertEqual(user_logs.count(), 1)
        self.assertEqual(user_logs[0], self.user_log)

    def tearDown(self):
        post_save.connect(receiver=user_kyc_profile_settings, sender=User)


class UserVerificationSettingTestCase(TestCase):
    def setUp(self):
        post_save.disconnect(receiver=user_kyc_profile_settings, sender=User)
        self.user = User.objects.create(username="testuser")

    def test_create_user_verification_setting(self):
        user_verification_setting = UserVerificationSetting.objects.create(
            kyc_status=1,
            photo_id="sample_photo_id",
            kyc_done=True,
            id_laminated=True,
            id_matched=True,
            scan_attempts=True,
            id_match_attempts=2,
            manual_verify=True,
            selfie=True,
            scanned=True,
            attachment="sample_attachment",
            account_details=True,
            profile_details=True,
            country_code="1",
            phone_number="123456789",
            phone_number_verified=True,
            verify_attempts=3,
            wrong_attempts=1,
            user=self.user,
        )

        self.assertEqual(UserVerificationSetting.objects.count(), 1)
        self.assertEqual(user_verification_setting.kyc_status, 1)
        self.assertEqual(user_verification_setting.phone_number, "123456789")

    def test_update_user_verification_setting(self):
        user_verification_setting = UserVerificationSetting.objects.create(
            kyc_status=1, photo_id="sample_photo_id", user=self.user
        )

        user_verification_setting.kyc_status = 2
        user_verification_setting.photo_id = "updated_photo_id"
        user_verification_setting.save()

        updated_verification_setting = UserVerificationSetting.objects.get(
            pk=user_verification_setting.pk
        )
        self.assertEqual(updated_verification_setting.kyc_status, 2)
        self.assertEqual(updated_verification_setting.photo_id, "updated_photo_id")

    def test_delete_user_verification_setting(self):
        user_verification_setting = UserVerificationSetting.objects.create(
            kyc_status=1, photo_id="sample_photo_id", user=self.user
        )

        user_verification_setting.delete()

        self.assertEqual(UserVerificationSetting.objects.count(), 0)

    def test_retrieve_user_verification_setting(self):
        user_verification_setting = UserVerificationSetting.objects.create(
            kyc_status=1, photo_id="sample_photo_id", user=self.user
        )

        retrieved_verification_setting = UserVerificationSetting.objects.get(
            pk=user_verification_setting.pk
        )

        self.assertEqual(retrieved_verification_setting.kyc_status, 1)
        self.assertEqual(retrieved_verification_setting.photo_id, "sample_photo_id")

    def tearDown(self):
        post_save.connect(receiver=user_kyc_profile_settings, sender=User)


class UserProfileTestCase(TestCase):
    def setUp(self):
        post_save.disconnect(receiver=user_kyc_profile_settings, sender=User)
        self.user = User.objects.create_user(username="testuser", password="test#1234")

    def test_create_user_profile(self):
        profile = UserProfile.objects.create(
            education=[EDUCATION_CHOICES[0][0]],
            income=INCOME_CHOICES[0][0],
            relationship_status=MARITAL_STATUS_CHOICES[0][0],
            interests=[INTEREST_CHOICES[0][0]],
            sports=[SPORTS_CHOICES[0][0]],
            about_me="About me text",
            skillset="Skillset text",
            experience="Experience text",
            profession="Profession text",
            iam_looking_for="Looking for text",
            political_interests="Political interests text",
            date_of_birth=datetime.now(),
            address="Address text",
            address1="Address1 text",
            city="City text",
            state="State text",
            postcode="Postcode text",
            company="Company text",
            role="Role text",
            gender=GENDER_CHOICES[0][0],
            chat_theme="http://example.com/chat-theme",
            team_size=5,
            sector=SECTORS_TYPE_CHOICES[0][0],
            user=self.user,
        )

        self.assertEqual(UserProfile.objects.count(), 1)
        self.assertEqual(profile.user, self.user)

    def test_update_user_profile(self):
        profile = UserProfile.objects.create(user=self.user)

        profile.education = [EDUCATION_CHOICES[1][0]]
        profile.save()

        updated_profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(updated_profile.education, [EDUCATION_CHOICES[1][0]])

    def test_delete_user_profile(self):
        profile = UserProfile.objects.create(user=self.user)

        profile.delete()

        self.assertEqual(UserProfile.objects.count(), 0)

    def test_related_name_logs(self):
        UserProfile.objects.create(user=self.user)
        user_profile = self.user.profile.all()
        self.assertEqual(user_profile.count(), 1)
        self.assertCountEqual(user_profile, UserProfile.objects.filter(user=self.user))

    def tearDown(self):
        post_save.connect(receiver=user_kyc_profile_settings, sender=User)


class DeviceInfoTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="testuser")

    def test_create_device_info(self):
        device_info = DeviceInfo.objects.create(
            device_id="123456789",
            os="Android",
            os_version="10",
            device_name="Samsung Galaxy S10",
            app_version="1.0.0",
            app_version_code="100",
            time_zone="UTC",
            user=self.user,
        )

        self.assertEqual(DeviceInfo.objects.count(), 1)
        self.assertEqual(device_info.device_id, "123456789")
        self.assertEqual(device_info.os, "Android")
        self.assertEqual(device_info.os_version, "10")
        self.assertEqual(device_info.device_name, "Samsung Galaxy S10")
        self.assertEqual(device_info.app_version, "1.0.0")
        self.assertEqual(device_info.app_version_code, "100")
        self.assertEqual(device_info.time_zone, "UTC")
        self.assertEqual(device_info.user, self.user)

    def test_update_device_info(self):
        device_info = DeviceInfo.objects.create(
            device_id="123456789",
            os="Android",
            os_version="10",
            device_name="Samsung Galaxy S10",
            app_version="1.0.0",
            app_version_code="100",
            time_zone="UTC",
            user=self.user,
        )

        device_info.device_name = "Samsung Galaxy S20"
        device_info.save()

        updated_device_info = DeviceInfo.objects.get(id=device_info.id)

        self.assertEqual(updated_device_info.device_name, "Samsung Galaxy S20")

    def test_delete_device_info(self):
        device_info = DeviceInfo.objects.create(
            device_id="123456789",
            os="Android",
            os_version="10",
            device_name="Samsung Galaxy S10",
            app_version="1.0.0",
            app_version_code="100",
            time_zone="UTC",
            user=self.user,
        )

        device_info.delete()

        self.assertEqual(DeviceInfo.objects.count(), 0)
        self.assertEqual(User.objects.count(), 1)

    def test_get_device_info(self):
        DeviceInfo.objects.create(
            device_id="123456789",
            os="Android",
            os_version="10",
            device_name="Samsung Galaxy S10",
            app_version="1.0.0",
            app_version_code="100",
            time_zone="UTC",
            user=self.user,
        )

        device_info = DeviceInfo.objects.get(device_id="123456789")

        self.assertEqual(device_info.device_name, "Samsung Galaxy S10")


class UserInviteTestCase(TestCase):
    def setUp(self):
        self.invited_by_user = User.objects.create(username="inviter")
        self.invited_user = User.objects.create(username="invitee")

    def test_create_user_invite(self):
        user_invite = UserInvite.objects.create(
            invited_user=self.invited_user,
            invited_by=self.invited_by_user,
        )

        self.assertEqual(UserInvite.objects.count(), 1)
        self.assertEqual(user_invite.invited_user, self.invited_user)
        self.assertEqual(user_invite.invited_by, self.invited_by_user)

    def test_delete_user_invite(self):
        user_invite = UserInvite.objects.create(
            invited_user=self.invited_user,
            invited_by=self.invited_by_user,
        )

        user_invite.delete()

        self.assertEqual(UserInvite.objects.count(), 0)

    def test_get_user_invites(self):
        UserInvite.objects.create(
            invited_user=self.invited_user,
            invited_by=self.invited_by_user,
        )

        invites = UserInvite.objects.filter(invited_user=self.invited_user)

        self.assertEqual(invites.count(), 1)
        self.assertEqual(invites[0].invited_user, self.invited_user)

    def test_get_invited_by_user(self):
        UserInvite.objects.create(
            invited_user=self.invited_user,
            invited_by=self.invited_by_user,
        )

        invites = UserInvite.objects.filter(invited_by=self.invited_by_user)

        self.assertEqual(invites.count(), 1)
        self.assertEqual(invites[0].invited_by, self.invited_by_user)


class UserDeviceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="testuser")
        self.device = UserDevice.objects.create(
            device_model="Device Model",
            device_os_version="Device OS Version",
            user=self.user,
        )

    def test_create_user_device(self):
        self.assertEqual(UserDevice.objects.count(), 1)
        self.assertEqual(self.device.device_model, "Device Model")
        self.assertEqual(self.device.device_os_version, "Device OS Version")
        self.assertEqual(self.device.user, self.user)

    def test_delete_user_device(self):
        self.device.delete()
        self.assertEqual(UserDevice.objects.count(), 0)

    def test_get_user_devices(self):
        devices = UserDevice.objects.filter(user=self.user)
        self.assertEqual(devices.count(), 1)
        self.assertEqual(devices[0].user, self.user)

    def test_user_devices_related_name(self):
        devices = self.user.devices.all()
        self.assertEqual(devices.count(), 1)
        self.assertEqual(devices[0], self.device)


class AppInfoTestCase(TestCase):
    def setUp(self):
        self.app_info = AppInfo.objects.create(
            name="Test App",
            current_version="1.0.0",
            last_compulsory_version="0.9.0",
            download_path="https://example.com/app",
        )

    def test_create_app_info(self):
        app_info_count = AppInfo.objects.count()
        self.assertEqual(app_info_count, 1)

    def test_read_app_info(self):
        app_info = AppInfo.objects.get(name="Test App")
        self.assertEqual(app_info.current_version, "1.0.0")
        self.assertEqual(app_info.last_compulsory_version, "0.9.0")
        self.assertEqual(app_info.download_path, "https://example.com/app")

    def test_update_app_info(self):
        app_info = AppInfo.objects.get(name="Test App")
        app_info.current_version = "2.0.0"
        app_info.save()

        updated_app_info = AppInfo.objects.get(name="Test App")
        self.assertEqual(updated_app_info.current_version, "2.0.0")

    def test_delete_app_info(self):
        app_info = AppInfo.objects.get(name="Test App")
        app_info.delete()

        app_info_count = AppInfo.objects.count()
        self.assertEqual(app_info_count, 0)


class LanguagesTestCase(TestCase):
    def setUp(self):
        self.language = Languages.objects.create(
            language="English",
            video_url="https://example.com/video",
            privacy_policy_url="https://example.com/privacy-policy",
            terms_conditions_url="https://example.com/terms-conditions",
            age_terms_ul="https://example.com/age-terms",
        )

    def test_create_language(self):
        language_count = Languages.objects.count()
        self.assertEqual(language_count, 1)

    def test_read_language(self):
        language = Languages.objects.get(language="English")
        self.assertEqual(language.video_url, "https://example.com/video")
        self.assertEqual(
            language.privacy_policy_url, "https://example.com/privacy-policy"
        )
        self.assertEqual(
            language.terms_conditions_url, "https://example.com/terms-conditions"
        )
        self.assertEqual(language.age_terms_ul, "https://example.com/age-terms")

    def test_update_language(self):
        language = Languages.objects.get(language="English")
        language.video_url = "https://example.com/new-video"
        language.save()

        updated_language = Languages.objects.get(language="English")
        self.assertEqual(updated_language.video_url, "https://example.com/new-video")

    def test_delete_language(self):
        language = Languages.objects.get(language="English")
        language.delete()

        language_count = Languages.objects.count()
        self.assertEqual(language_count, 0)


class SignalHandlerTestCase(TestCase):
    """Signals Testing"""

    def setUp(self):
        self.user = User.objects.create(username="testuser")

    def test_user_kyc_profile_settings(self):
        post_save.connect(receiver=user_kyc_profile_settings, sender=User)
        self.user.save()

        self.assertTrue(UserLog.objects.filter(user=self.user).exists())
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())
        self.assertTrue(
            UserVerificationSetting.objects.filter(
                user=self.user, photo_id="0"
            ).exists()
        )

        post_save.disconnect(receiver=user_kyc_profile_settings, sender=User)


"""Field Validation and Model Relationship"""


class UserFieldValidationTest(TestCase):
    def test_user_name_max_length(self):
        user = User(username="testuser", name="A" * 101)
        with self.assertRaises(ValidationError) as context:
            user.full_clean()
        self.assertTrue("name" in context.exception.error_dict)

    def test_wrong_country_code(self):
        country_code = "91"
        with self.assertRaises(ValidationError):
            setting = User(
                country_code=country_code,
            )
            setting.full_clean()

    def test_phone_number_max_length(self):
        user = User.objects.create(username="testuser")
        user.phone_number = "1234567890123456789012345678901"
        with self.assertRaises(ValidationError) as context:
            user.full_clean()
        self.assertTrue("phone_number" in context.exception.error_dict)

    def test_phone_number_verified_default(self):
        user = User.objects.create(username="testuser")
        self.assertFalse(user.phone_number_verified)

    def test_is_business_default(self):
        user = User.objects.create(username="testuser")
        self.assertFalse(user.is_business)

    def test_login_attempts_default(self):
        user = User.objects.create(username="testuser")
        self.assertEqual(user.login_attempts, 0)

    def test_user_type_max_length(self):
        user = User.objects.create(username="testuser")
        user.user_type = "A" * 16
        with self.assertRaises(ValidationError) as context:
            user.full_clean()
        self.assertTrue("user_type" in context.exception.error_dict)


class UserLogFieldValidationTest(TestCase):
    def setUp(self):
        post_save.disconnect(receiver=user_kyc_profile_settings, sender=User)
        self.user = User.objects.create(username="testuser")

    def test_s3_logs_null_or_blank(self):
        log = UserLog.objects.create(s3_logs=None, kyc_logs="KYC logs", user=self.user)
        self.assertIsNone(log.s3_logs)

        log.s3_logs = ""
        log.save()
        self.assertEqual(log.s3_logs, "")

    def test_kyc_logs_null_or_blank(self):
        log = UserLog.objects.create(s3_logs="S3 logs", kyc_logs=None, user=self.user)
        self.assertIsNone(log.kyc_logs)

        log.kyc_logs = ""
        log.save()
        self.assertEqual(log.kyc_logs, "")

    def test_relationship_with_user(self):
        log = UserLog.objects.create(user=self.user)
        log.save()
        self.assertEqual(log.user, self.user)
        self.assertEqual(log, self.user.logs.first())

    def tearDown(self):
        post_save.connect(receiver=user_kyc_profile_settings, sender=User)


class UserDeviceFieldValidationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="testuser")

    def test_device_model_max_length(self):
        device = UserDevice.objects.create(
            device_model="A" * 101, device_os_version="1.0", user=self.user
        )
        with self.assertRaises(ValidationError) as context:
            device.full_clean()
        self.assertTrue("device_model" in context.exception.error_dict)

    def test_device_os_version_max_length(self):
        device = UserDevice.objects.create(
            device_model="Device 1", device_os_version="B" * 101, user=self.user
        )
        with self.assertRaises(ValidationError) as context:
            device.full_clean()
        self.assertTrue("device_os_version" in context.exception.error_dict)

    def test_relationship_with_user(self):
        device = UserDevice.objects.create(
            device_model="Device 1", device_os_version="12.24", user=self.user
        )
        device.save()
        self.assertEqual(device.user, self.user)
        self.assertEqual(device, self.user.devices.first())


class UserVerificationSettingFieldValidationTest(TestCase):
    def setUp(self):
        post_save.disconnect(receiver=user_kyc_profile_settings, sender=User)
        self.user = User.objects.create(username="testuser")

    def test_kyc_status_choices(self):
        invalid_status = 99
        with self.assertRaises(ValidationError):
            setting = UserVerificationSetting(
                kyc_status=invalid_status, photo_id="123456", user=self.user
            )
            setting.full_clean()

    def test_phone_number_length(self):
        long_phone_number = "1234567890123456789012345678901"
        with self.assertRaises(ValidationError):
            setting = UserVerificationSetting(
                phone_number=long_phone_number, photo_id="123456", user=self.user
            )
            setting.full_clean()

    def test_wrong_country_code(self):
        country_code = "13"
        with self.assertRaises(ValidationError):
            setting = UserVerificationSetting(
                country_code=country_code, photo_id="123456", user=self.user
            )
            setting.full_clean()

    def test_relationship_with_user(self):
        setting = UserVerificationSetting(photo_id="123456", user=self.user)
        setting.save()
        self.assertEqual(setting.user, self.user)
        self.assertEqual(setting, self.user.settings.first())

    def tearDown(self):
        post_save.connect(receiver=user_kyc_profile_settings, sender=User)


class UserProfileFieldValidationTest(TestCase):
    def setUp(self):
        post_save.disconnect(receiver=user_kyc_profile_settings, sender=User)
        self.user = User.objects.create(username="testuser")

    def test_max_length_constraints(self):
        max_length_education = 100
        max_length_interests = 1024
        max_length_sports = 100
        max_length_skillset = 250
        max_length_experience = 250
        max_length_profession = 55
        max_length_political_interests = 250
        max_length_address = 250
        max_length_city = 55
        max_length_state = 55
        max_length_company = 255
        max_length_role = 255
        max_length_gender = 10
        max_length_chat_theme = 255

        profile = UserProfile(
            education=["High School"] * (max_length_education + 1),
            interests=["Music"] * (max_length_interests + 1),
            sports=["Basketball"] * (max_length_sports + 1),
            skillset="A" * (max_length_skillset + 1),
            experience="B" * (max_length_experience + 1),
            profession="C" * (max_length_profession + 1),
            political_interests="D" * (max_length_political_interests + 1),
            address="E" * (max_length_address + 1),
            city="F" * (max_length_city + 1),
            state="G" * (max_length_state + 1),
            company="H" * (max_length_company + 1),
            role="I" * (max_length_role + 1),
            gender="J" * (max_length_gender + 1),
            chat_theme="http://example.com/" + "K" * (max_length_chat_theme - 18),
            user=self.user,
        )
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_blank_fields(self):
        profile = UserProfile(user=self.user, gender=GENDER_CHOICES[0][0])
        profile.full_clean()

    def test_user_relationship(self):
        profile = UserProfile(
            education=["High School"],
            interests=["Music"],
            sports=["Basketball"],
            skillset="Programming",
            experience="5 years",
            profession="Engineer",
            political_interests="Environment",
            address="123 Street",
            city="New York",
            state="NY",
            company="ABC Corp",
            role="Developer",
            gender="Male",
            chat_theme="http://example.com/theme",
            user=self.user,
        )
        profile.save()
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile, self.user.profile.first())

    def tearDown(self):
        post_save.connect(receiver=user_kyc_profile_settings, sender=User)


class DeviceInfoFieldValidationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="testuser")

    def test_max_length_constraints(self):
        max_length = 300
        device_info = DeviceInfo(
            device_id="A" * (max_length + 1),
            os="B" * (max_length + 1),
            os_version="C" * (max_length + 1),
            device_name="D" * (max_length + 1),
            app_version="E" * (max_length + 1),
            app_version_code="F" * (max_length + 1),
            time_zone="G" * (max_length + 1),
            user=self.user,
        )
        with self.assertRaises(ValidationError):
            device_info.full_clean()

    def test_blank_fields(self):
        device_info = DeviceInfo(user=self.user)
        device_info.full_clean()

    def test_user_relationship(self):
        # Test user relationship
        device_info = DeviceInfo(
            device_id="123456",
            os="Android",
            os_version="10.0",
            device_name="Samsung Galaxy S10",
            app_version="1.0",
            app_version_code="100",
            time_zone="UTC",
            user=self.user,
        )
        device_info.save()
        self.assertEqual(device_info.user, self.user)
        self.assertIn(device_info, self.user.device_info.all())


class AppInfoFieldValidationTest(TestCase):
    def test_max_length_constraints(self):
        max_length = 300
        app_info = AppInfo(
            name="A" * (max_length + 1),
            current_version="B" * (max_length + 1),
            last_compulsory_version="C" * (max_length + 1),
            download_path="D" * (max_length + 1),
        )
        with self.assertRaises(ValidationError):
            app_info.full_clean()

    def test_blank_fields(self):
        app_info = AppInfo()
        app_info.full_clean()


class LanguagesFieldValidationTest(TestCase):
    def test_language_max_length(self):
        max_length = Languages._meta.get_field("language").max_length
        language = Languages(language="a" * (max_length + 1))
        with self.assertRaises(ValidationError):
            language.full_clean()

    def test_url_max_length(self):
        max_length = 300
        language = Languages(
            language="English",
            video_url="https://example.com/"
            + "a" * (max_length - len("https://example.com/") + 1),
            privacy_policy_url="https://example.com/"
            + "a" * (max_length - len("https://example.com/") + 1),
            terms_conditions_url="https://example.com/"
            + "a" * (max_length - len("https://example.com/") + 1),
            age_terms_ul="https://example.com/"
            + "a" * (max_length - len("https://example.com/") + 1),
        )
        with self.assertRaises(ValidationError):
            language.full_clean()

    def test_blank_fields(self):
        language = Languages()
        language.full_clean()


class MuteConversationFieldValidationTest(TestCase):
    def test_sender_id_max_length(self):
        max_length = MuteConversation._meta.get_field("sender_id").max_length
        mute_conversation = MuteConversation(
            sender_id="a" * (max_length + 1), recipient_id="12345"
        )
        with self.assertRaises(ValidationError):
            mute_conversation.full_clean()

    def test_recipient_id_max_length(self):
        max_length = MuteConversation._meta.get_field("recipient_id").max_length
        mute_conversation = MuteConversation(
            sender_id="54321", recipient_id="b" * (max_length + 1)
        )
        with self.assertRaises(ValidationError):
            mute_conversation.full_clean()

    def test_mute_default_value(self):
        mute_conversation = MuteConversation(sender_id="54321", recipient_id="12345")
        self.assertEqual(mute_conversation.mute, False)

    def test_mute_time_default_value(self):
        mute_conversation = MuteConversation(sender_id="54321", recipient_id="12345")
        self.assertEqual(mute_conversation.mute_time, 0)

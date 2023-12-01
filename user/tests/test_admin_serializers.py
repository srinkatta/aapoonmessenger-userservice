from unittest.mock import MagicMock, patch

from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from user.api.admin.serializers import *
from user.models import *


class UserListSerializerTestCase(APITestCase):
    def setUp(self):
        # Create sample user data for testing
        self.user_data = {
            "id": 1,  # User ID
            "username": "testuser",  # User's username
            "email": "test@example.com",  # User's email
            "date_joined": "2023-08-01T12:00:00Z",  # Date user joined
            "country_code": "US",  # User's country code
            "phone_number": "1234567890",  # User's phone number
            "phone_number_verified": True,  # User's phone number verification status
            "user_type": "regular",  # User's type (e.g., regular, admin)
        }

        # Create a user using the sample user data
        self.user = User.objects.create(**self.user_data)

    def test_user_list_serializer(self):
        # Serialize the user instance using UserListSerializer
        serializer = UserListSerializer(instance=self.user)

        # Define the expected data structure based on user_data
        expected_data = {
            "id": self.user_data["id"],  # User ID
            "user_name": self.user_data["username"],  # User's username
            "email": self.user_data["email"],  # User's email
            "date_joined": self.user_data["date_joined"],  # Date user joined
            "country": self.user_data["country_code"],  # User's country code
            "phone_number": self.user_data["phone_number"],  # User's phone number
            "phone_verified": self.user_data[
                "phone_number_verified"
            ],  # Phone verification status
            "kyc_verified": False,  # Replace with the expected value for KYC verification
            "user_type": self.user_data[
                "user_type"
            ],  # User's type (e.g., regular, admin)
        }

        # Assert that the serialized data matches the expected data
        self.assertEqual(serializer.data, expected_data)


class UserDetailSerializerTestCase(APITestCase):
    def setUp(self):
        # Create a sample user for testing
        self.user = User.objects.create(
            name="John Doe",  # User's name
            email="johndoe@example.com",  # User's email
            country_code="+1",  # User's country code
            phone_number="1234567890",  # User's phone number
            # phone_verified=True,  # Adjust this based on actual data
            # last_login=datetime.now()  # Adjust this based on actual data
        )

    def test_user_detail_serializer(self):
        # Serialize the user instance using UserDetailSerializer
        serializer = UserDetailSerializer(instance=self.user)

        # Define the expected data structure based on user's attributes
        expected_data = {
            "id": self.user.id,  # User ID
            "name": "John Doe",  # User's name
            "email": "johndoe@example.com",  # User's email
            "country_code": "+1",  # User's country code
            "phone_number": "1234567890",  # User's phone number
            "phone_verified": False,  # Adjust this based on actual data
            "kyc_logs": None,  # Adjust this based on your data
            "kyc_image": None,  # Modify this if kyc_image is expected to be non-empty
            "last_login": None,  # Adjust this based on actual data
        }

        # Assert that the serialized data matches the expected data
        self.assertEqual(serializer.data, expected_data)


class UserVerificationSerializerTestCase(APITestCase):
    def setUp(self):
        # Create a sample user for testing
        self.user = User.objects.create(
            username="testuser",  # User's username
            phone_number="123456789",  # User's phone number
            country_code="+1",  # User's country code
        )
        # Create a UserVerificationSetting for the user
        self.user_verification_setting = UserVerificationSetting.objects.create(
            user=self.user,  # Assign the user to the verification setting
            kyc_done=True,  # Set KYC verification as done
        )

    def test_user_verification_serializer(self):
        # Serialize the user verification setting using UserVerificationSerializer
        serializer = UserVerificationSerializer(instance=self.user_verification_setting)

        # Define the expected data structure based on user verification attributes
        expected_data = {
            "user_id": self.user.id,  # User ID
            "phone": "123456789+1",  # Formatted phone number with country code
            "kyc_done": True,  # KYC verification status
        }

        # Assert that the serialized data matches the expected data
        self.assertEqual(serializer.data, expected_data)


class UserVerificationUpdateSerializerTestCase(APITestCase):
    def setUp(self):
        # Create a sample user for testing
        self.user = User.objects.create(
            username="testuser",  # User's username
            phone_number="123456789",  # User's phone number
            country_code="+1",  # User's country code
        )
        # Create a UserVerificationSetting for the user
        self.user_verification_setting = UserVerificationSetting.objects.create(
            user=self.user,  # Assign the user to the verification setting
            kyc_done=True,  # Set KYC verification as done
        )

    def test_user_verification_update_serializer(self):
        # Serialize the user verification setting using UserVerificationUpdateSerializer
        serializer = UserVerificationUpdateSerializer(
            instance=self.user_verification_setting
        )

        # Define the expected data structure for user verification update
        expected_data = {
            "user_id": self.user.id,  # User ID
            "kyc_done": True,  # KYC verification status
        }

        # Assert that the serialized data matches the expected data
        self.assertEqual(serializer.data, expected_data)


class UserFilterSerializerTestCase(APITestCase):
    def setUp(self):
        # Create a sample user for testing
        self.user = User.objects.create(
            username="testuser",  # User's username
            phone_number="123456789",  # User's phone number
            country_code="+1",  # User's country code
            phone_number_verified=True,  # User's phone number verification status
            user_type="regular",  # User's type
        )

    def test_user_filter_serializer(self):
        # Serialize the user using UserFilterSerializer
        serializer = UserFilterSerializer(instance=self.user)

        # Define the expected data structure for filtered user serialization
        expected_data = {
            "id": self.user.id,  # User ID
            "date_joined": self.user.date_joined.strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),  # Joined date
            "country_code": self.user.country_code,  # User's country code
            "phone_number": self.user.phone_number,  # User's phone number
            "phone_number_verified": self.user.phone_number_verified,  # Phone number verification status
            "kyc_verified": self.user.settings.get().kyc_done,  # KYC verification status
            "user_type": self.user.user_type,  # User type
        }

        # Assert that the serialized data matches the expected data
        self.assertEqual(serializer.data, expected_data)


class DeletedUserSerializerTest(APITestCase):
    def setUp(self):
        # Define sample user data for testing
        self.user_data = {
            "username": "testuser",  # User's username
            "email": "test@example.com",  # User's email
        }

        # Define data for a deleted user with associated user_data and is_deleted status
        self.deleted_user_data = {
            "user": self.user_data,  # Reference to the user data
            "is_deleted": True,  # Marked as deleted
        }

        # Define serializer data for a deleted user with ID, user data, and is_deleted status
        self.serializer_data = {
            "id": 1,  # User ID
            "user": self.user_data,  # Reference to the user data
            "is_deleted": True,  # Marked as deleted
        }

    def test_deleted_user_serializer(self):
        # Create a serializer instance using the deleted_user_data
        serializer = DeletedUserSerializer(data=self.deleted_user_data)

        # Assert that the serializer is not valid (as expected)
        self.assertFalse(serializer.is_valid())


class CreateSuperUserSerializerTest(APITestCase):
    def setUp(self):
        # Define valid data for creating a superuser
        self.valid_data = {
            "phone_number": "1234567890",  # Phone number
            "country_code": "+1",  # Country code
            "email": "test@example.com",  # Email (optional)
            "username": "testuser",  # Username
            "password": "testpassword",  # Password
        }

    def test_create_super_user_serializer_valid_data(self):
        # Create a serializer instance using the valid_data
        serializer = CreateSuperUserSerializer(data=self.valid_data)

        # Assert that the serializer is valid (as expected)
        self.assertTrue(serializer.is_valid())

    def test_create_super_user_serializer_invalid_data(self):
        # Define invalid data with missing required fields
        invalid_data = {
            "phone_number": "1234567890",  # Phone number
            "country_code": "+1",  # Country code
            "username": "testuser",  # Username
        }

        # Create a serializer instance using the invalid_data
        serializer = CreateSuperUserSerializer(data=invalid_data)

        # Assert that the serializer is not valid (as expected)
        self.assertFalse(serializer.is_valid())


class SuperUserLoginSerializerTest(APITestCase):
    def setUp(self):
        # Define superuser login data
        self.superuser_data = {
            "username": "admin",  # Superuser username
            "password": "adminpassword",  # Superuser password
        }

    def test_superuser_login_serializer_valid_data(self):
        # Create a serializer instance using the superuser_data
        serializer = SuperUserLoginSerializer(data=self.superuser_data)

        # Assert that the serializer is valid (as expected)
        self.assertTrue(serializer.is_valid())

    def test_superuser_login_serializer_invalid_data(self):
        # Define invalid data with missing required fields
        invalid_data = {
            "username": "admin",  # Superuser username
            # Missing password
        }

        # Create a serializer instance using the invalid_data
        serializer = SuperUserLoginSerializer(data=invalid_data)

        # Assert that the serializer is not valid (as expected)
        self.assertFalse(serializer.is_valid())

    def test_superuser_login_deserialization(self):
        # Create a serializer instance using the superuser_data
        serializer = SuperUserLoginSerializer(data=self.superuser_data)

        # Validate the serializer
        serializer.is_valid()

        # Get the validated user_instance
        user_instance = serializer.validated_data

        # Assert that the username matches the expected value
        self.assertEqual(user_instance["username"], "admin")

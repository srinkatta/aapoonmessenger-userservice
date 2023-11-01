import json
from unittest.mock import patch

import mock
from django.urls import reverse
from httmock import all_requests
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.test import APITestCase, MockOriginalResponse

from user.api.serializers import *
from user.api.viewsets import *
from user.helpers.otp import generate_otp
from user.helpers.sms import *
from user.models import *
from user.models import User

# from user.api import AuthUserRegistrationView


class RegistrationAPITestCase(APITestCase):
    def setUp(self):
        self.register_url = "/api/users/auth/register/"
        self.login_url = "/api/users/auth/login/"
        self.client = self.client_class()
        self.jwt_token: str | None = None

    def test_register_user(self):
        # Send a POST request to register a user
        data = {
            "name": "aapoon",
            "country_code": "91",
            "phone_number": "9603753594",
            "kyc_done": True,
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert that a user with the specified username was created
        user = User.objects.get(country_code="91", phone_number="9603753594")
        self.assertIsNotNone(user)

    def test_login_and_retrieve_jwt(self):
        # Create a user
        otp = generate_otp()
        self.user1 = User.objects.create_user(
            username="aapoon-12234",
            name="aapoon",
            country_code="91",
            phone_number="9603753594",
            otp_requested=otp,
        )

        # Send a POST request to log in and retrieve the JWT token
        data1 = {"country_code": "91", "phone_number": "9603753594", "otp": otp}
        response1 = self.client.post(self.login_url, data1)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Retrieve and store the JWT token for subsequent requests
        self.jwt_token1 = response1.data["access"]
        self.assertIsNotNone(self.jwt_token1)

    def test_authenticated_endpoint(self):
        # Send a GET request to an authenticated endpoint using the stored JWT token
        self.test_login_and_retrieve_jwt()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.jwt_token1)
        response = self.client.get("/api/users/profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AuthUserRegisterTest(APITestCase):
    def setUp(self):
        User.objects.create_user(
            username="anjan", email="xyz@gmail.com", password="abc123"
        )
        User.objects.create_user(
            username="testuser1",
            country_code="91",
            phone_number="9110043114",
            password="test_123Dffa",
        )
        self.client = self.client_class()

    def test_existing_user_with_email(self):
        """Sending request from a existing user"""
        payload = dict(
            name="anjan",
            email="xyz@gmail.com",
            country_code="91",
            phone_number="9898989898",
            password="abc123",
        )

        response = self.client.post("/api/users/auth/register/", data=payload)

        self.assertEqual(
            response.data["detail"],
            "A user is already registered with this e-mail address.",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_existing_user_without_email(self):

        payload = dict(country_code="91", phone_number="9110043114")

        with mock.patch.object(RegisterSerializer, "send_otp") as mocked_function:
            mocked_function.status_code = status.HTTP_200_OK

            response = self.client.post("/api/users/auth/register/", data=payload)
            self.assertEqual(response.status_code, 200)
            mocked_function.assert_called_once()
            self.assertEqual(User.objects.count(), 2)

    def test_new_user(self):
        payload = dict(
            country_code="1",
            phone_number="6469804599",
            device_model="iPhone 13",
            device_os_version="16.5",
        )

        with mock.patch.object(RegisterSerializer, "send_otp") as mocked_function:
            mocked_function.status_code = status.HTTP_200_OK

            response = self.client.post("/api/users/auth/register/", data=payload)
            mocked_function.assert_called_once()
            self.assertEqual(UserDevice.objects.count(), 1)
            self.assertEqual(User.objects.count(), 3)


class AuthUserLoginView(APITestCase):
    def setUp(self):
        otp = generate_otp()
        User.objects.create_user(
            username="user1", email="anjan@gmail.com", password="abc123"
        )
        User.objects.create_user(
            username="user2",
            country_code="91",
            phone_number="9110043114",
            password="test_123Dffa",
            otp_requested=otp,
        )
        self.client = self.client_class()

    def test_invalid_user_login(self):
        data = dict(
            name="anjan",
            email="testcase@gmail.com",
            country_code="91",
            phone_number="9856985698",
            password="114101121",
        )

        response = self.client.post("/api/users/auth/login/", data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_with_invalid_otp(self):
        otp = generate_otp()

        data = {"country_code": "91", "phone_number": "9110043114", "otp": otp}
        response = self.client.post("/api/users/auth/login/", data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_with_valid_otp_and_login_credentials_and_retreive_jwt(self):
        otp = "256314"
        User.objects.create_user(
            username="testuser3",
            country_code="91",
            phone_number="9603753594",
            password="testcases",
            otp_requested=otp,
        )

        data = {"country_code": "91", "phone_number": "9603753594", "otp": otp}
        response = self.client.post("/api/users/auth/login/", data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.jwt_token = response.data["access"]
        self.assertIsNotNone(self.jwt_token)


class Auth_send_otp_view(APITestCase):
    def setUp(self):
        self.url = "/api/users/auth/send_otp/"
        self.client = self.client_class()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )
        self.client.force_authenticate(user=self.user)

    def test_send_otp_existing_phone_number(self):
        # Create a user with an existing phone number
        User.objects.create_user(
            username="existinguser",
            password="testpassword",
            phone_number="1234567890",
            country_code="91",
        )

        # Send a POST request with the same phone number
        data = {"phone_number": "1234567890", "country_code": "91"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Mobile number already exists")

    def test_send_otp_invalid_phone_number(self):
        data = {"phone_number": "invalid", "country_code": "91"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Special characters not allowed")

    def test_max_phone_attempts(self):

        data = dict(
            country_code="91",
            phone_number="9856985698",
        )

        with mock.patch.object(SendOTPView, "max_phone_attempts") as mocked_function:
            mocked_function.return_value = Response(
                status=status.HTTP_200_OK,
            )

        response = self.client.post(self.url, data=data)

        # Verify that the response has a status code of 200
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_send_otp_with_get(self):
        data = dict(
            country_code="91",
            phone_number="9856985698",
        )

        with mock.patch.object(SendOTPView, "send_otp") as mocked_function:
            mocked_function.return_value = Response(
                status=status.HTTP_200_OK,
            )

        response = self.client.post(self.url, data=data)

        # Verify that the response has a status code of 200
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_send_otp_success_with_post(self):
        # Mock the necessary dependencies and set up test data
        country_code = "91"
        phone_number = "9856985698"
        otp = "122708"

        with mock.patch("user.helpers.sms.FAST_SMS") as MockFastSMS:
            mock_fast_sms_instance = MockFastSMS.return_value
            mock_fast_sms_instance.send_message.return_value = True

            response = self.client.post(
                self.url,
                data={
                    "country_code": country_code,
                    "phone_number": phone_number,
                    "otp": otp,
                },
            )

            # Verify that the response has a status code of 200
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class VerifyPhoneViewTestCase(APITestCase):
    def setUp(self):
        self.url = "/api/users/auth/verify_otp/"
        otp = "1234"
        self.user = User.objects.create_user(
            username="user2",
            country_code="91",
            phone_number="9110043114",
            password="test_123Dffa",
            otp_requested=otp,
        )
        self.client = self.client_class()

    def test_successful_phone_number_verification(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "otp": "1234",
        }
        # Mocking Request and Serializer to validate and handle exceptions
        with patch("user.utils.make_request") as mock_make_request:
            mock_make_request.return_value = Response(
                status=status.HTTP_200_OK,
            )
        with mock.patch.object(
            VerifyPhoneSerializer, "phone_validate"
        ) as mocked_function:
            mocked_function.return_value = Response(
                status=status.HTTP_200_OK,
            )

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Phone Number successfully verified")

    def test_phone_number_verification_Incorrect_otp(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "otp": "12334",
        }

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserProfileViewSetTestCase(APITestCase):
    def setUp(self):
        # Create a user with authentication credentials
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword",
            name="John Doe",
            email="johndoe@example.com",
            country_iso_code="US",
            is_business=False,
        )
        self.client = self.client_class()
        self.url = "/api/users/profile/"

    def test_retrieve_user_profile(self):
        # Authenticate the user
        self.client.force_authenticate(user=self.user)

        # Send a GET request to retrieve the user profile
        response = self.client.get(self.url)

        # Check the response status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check the retrieved user profile data
        self.assertEqual(User.objects.count(), 1)


class UserViewSetTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )
        self.client = self.client_class()
        self.client.login(username="testuser", password="testpassword")
        self.url = "/api/users/user/"

    def test_list_users(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_user(self):

        response = self.client.get(self.url, kwargs={"pk": self.user.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_head_user(self):
        response = self.client.get(self.url, kwargs={"pk": self.user.pk})
        response = self.client.head(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class UserDeleteRequestViewTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )
        self.client.force_authenticate(user=self.user)
        self.url = "/api/users/user_delete/"

    def test_delete_user(self):

        data = {"user_id": self.user.id}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "User added to be deleted list.")

    def test_delete_user_invalid(self):
        data = {"user_id": 9999}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(
            response.data["detail"],
            "Sorry, We are  facing an issue currently. Thanks for noticing . We fix it soon.",
        )


class UserDeleteRevokeViewTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )
        self.client.force_authenticate(user=self.user)
        self.url = "/api/users/user/delete/revoke/"

    def test_revoke_user_deletion(self):
        deleted_user = DeletedUser.objects.create(user=self.user)
        data = {"user_id": str(self.user.id)}

        # Perform the API request to revoke the user deletion
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "User deletion action revoked")

        # Assert that the deleted user no longer exists in the database
        self.assertFalse(DeletedUser.objects.filter(user=self.user).exists())

    def test_revoke_user_deletion_invalid_user(self):

        data = {"user_id": 9999}  # Non-existent user ID

        # Perform the API request to revoke the user deletion
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "User deletion action revoked")


class UserDeleteCronViewTestCase(APITestCase):
    def setUp(self):

        self.url = "/api/users/user_delete/cron/"
        self.client = self.client_class()

    def test_get_deleted_users(self):
        # Create some users
        user1 = User.objects.create(username="user1")
        user2 = User.objects.create(username="user2")
        user3 = User.objects.create(username="user3")

        # Create deleted users linked to the respective users
        deleted_user1 = DeletedUser.objects.create(user=user1)
        deleted_user2 = DeletedUser.objects.create(user=user2)
        deleted_user3 = DeletedUser.objects.create(user=user3)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "User's deleted successfully.")


class InviteListViewTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )
        self.client.force_authenticate(user=self.user)
        self.url = "/api/users/invite_list/"

    def test_get_invite_user_list(self):
        # Create some user invites
        invite1 = UserInvite.objects.create(invited_by=self.user)
        invite2 = UserInvite.objects.create(invited_by=self.user)
        invite3 = UserInvite.objects.create(invited_by=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertEqual(response.headers['Content-Type'], 'application/vnd.ms-excel')

    def test_get_invite_user_list_no_invites(self):
        UserInvite.objects.filter(invited_by=self.user).delete()

        response = self.client.get(reverse("get_invite_list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class UserCheckAPIViewTestCase(APITestCase):
    def test_user_check(self):
        url = "/api/users/user_friends_check/"
        contacts = [
            {"contactName": "John Doe", "contactPhoneNumber": "1234567890"},
            {"contactName": "Jane Smith", "contactPhoneNumber": "9876543210"},
        ]

        data = {"contacts": contacts}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), len(contacts))
        self.assertEqual(response.data[0]["aapoonUser"], False)

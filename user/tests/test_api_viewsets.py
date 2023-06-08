from rest_framework.test import APITestCase
from rest_framework.test import APIClient
from rest_framework import status

from user.models import User, UserDevice, UserInvite
from user.api.serializers import RegisterSerializer

from unittest import mock


class AuthUserRegisterTest(APITestCase):
    def setUp(self):
        User.objects.create_user(
            username="aryan", email="xyz@gmail.com", password="abc123"
        )
        User.objects.create_user(
            username="testuser1",
            country_code="91",
            phone_number="9110043114",
            password="test_123Dffa",
        )
        self.apiclient = APIClient()

    def test_existing_user_with_email(self):
        """Sending request from a existing user"""
        payload = dict(
            name="aryan",
            email="xyz@gmail.com",
            country_code="91",
            phone_number="9000000001",
            password="abc123",
        )

        response = self.apiclient.post("/api/users/auth/register/", data=payload)
        self.assertEqual(
            response.data["detail"],
            "A user is already registered with this e-mail address.",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_from_na_country(self):
        """Sending request from unavailable country"""
        payload = dict(
            name="newuser",
            email="newuser@gmail.com",
            country_code="33",
            phone_number="0525215442",
            password="test#1234",
        )

        err_message = (
            "Thank you for your interest in aapoon. We contact you as soon as "
            "aapoon is available in your country."
        )

        response = self.apiclient.post("/api/users/auth/register/", data=payload)
        self.assertEqual(response.data["detail"], err_message)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 2)

    def test_existing_user_without_email(self):
        payload = dict(country_code="91", phone_number="9110043114")

        with mock.patch.object(RegisterSerializer, "send_otp") as mocked_function:
            mocked_function.status_code = status.HTTP_200_OK

            response = self.apiclient.post("/api/users/auth/register/", data=payload)
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

            response = self.apiclient.post("/api/users/auth/register/", data=payload)
            self.assertEqual(response.status_code, 200)
            mocked_function.assert_called_once()
            self.assertEqual(UserDevice.objects.count(), 1)
            self.assertEqual(User.objects.count(), 3)

    def test_new_user_with_invite(self):
        payload = dict(
            name="newuser",
            email="newuser@gmail.com",
            country_code="971",
            phone_number="553001615",
            password="test#1234",
            invited_by="1",
        )

        with mock.patch.object(RegisterSerializer, "send_otp") as mocked_function:
            mocked_function.status_code = status.HTTP_200_OK

            response = self.apiclient.post("/api/users/auth/register/", data=payload)
            self.assertEqual(response.status_code, 200)
            mocked_function.assert_called_once()
            self.assertEqual(UserInvite.objects.count(), 1)
            self.assertEqual(User.objects.count(), 3)

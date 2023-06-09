from user.models import User
from rest_framework.test import APITestCase, MockOriginalResponse
from rest_framework import status
from httmock import all_requests
from user.helpers.otp import generate_otp
import json
import mock
from django.urls import reverse
from rest_framework.pagination import PageNumberPagination
from unittest.mock import patch
from user.api.serializers import *
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
            "kyc_done":True,
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
            username="anjan", 
            email="xyz@gmail.com", 
            password="abc123"
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
        payload = dict(country_code="91", phone_number="9603753594")

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
            username="user1", 
            email="anjan@gmail.com", 
            password="abc123"
        )
        User.objects.create_user(
            username="user2",
            country_code="91",
            phone_number="9110043114",
            password="test_123Dffa",
            otp_requested=otp
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
            otp_requested=otp
        )
        
        data = {"country_code": "91", "phone_number": "9603753594", "otp": otp}
        response = self.client.post("/api/users/auth/login/", data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.jwt_token = response.data["access"]
        self.assertIsNotNone(self.jwt_token)
    
        


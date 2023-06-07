from user.models import User
from rest_framework.test import APITestCase, MockOriginalResponse
from rest_framework import status
from httmock import all_requests
from user.helpers.otp import generate_otp
import json
from django.urls import reverse
from rest_framework.pagination import PageNumberPagination
from unittest.mock import patch
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
            "phone_number": "9177098661",
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert that a user with the specified username was created
        user = User.objects.get(country_code="91", phone_number="9177098661")
        self.assertIsNotNone(user)

    def test_login_and_retrieve_jwt(self):
        # Create a user
        otp = generate_otp()
        self.user1 = User.objects.create_user(
            username="aapoon-12234",
            name="aapoon",
            country_code="91",
            phone_number="9177098661",
            otp_requested=otp,
        )   

        self.user2 = User.objects.create_user(
            username="aapoon-12345",
            name="aapoon digital",
            country_code="91",
            phone_number="9177098671",
            otp_requested=otp,
        )

        # Send a POST request to log in and retrieve the JWT token
        data1 = {"country_code": "91", "phone_number": "9177098661", "otp": otp}
        data2 = {"country_code": "91", "phone_number": "9177098671", "otp": otp}
        response1 = self.client.post(self.login_url, data1)
        response2 = self.client.post(self.login_url, data2)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # Retrieve and store the JWT token for subsequent requests
        self.jwt_token1 = response1.data["access"]
        self.assertIsNotNone(self.jwt_token1)

        self.jwt_token2 = response2.data["access"]
        self.assertIsNotNone(self.jwt_token2)

    def test_authenticated_endpoint(self):
        # Send a GET request to an authenticated endpoint using the stored JWT token
        self.test_login_and_retrieve_jwt()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.jwt_token1)
        response = self.client.get("/api/users/profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_by_id_and_total_list(self):
        # Send a GET request to retrieve the list of users
        self.test_login_and_retrieve_jwt()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.jwt_token1)
        response = self.client.get("/api/users/profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(User.objects.get(id=1), self.user1)
        self.assertEqual(User.objects.count(), 2)

    def test_pagination_user_list(self):
        # Create a request
        
        self.test_login_and_retrieve_jwt()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.jwt_token1)

        # Test pagination
        request = self.client.get ("/api/users/profile/", {'page': 2})
        response = self.client.get("/api/users/profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
  

    def test_update_user_verification_settings(self):
        self.test_login_and_retrieve_jwt()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.jwt_token1)
        res = self.client.get("/api/users/admin-panel/verify/settings/")

        # Prepare the request data
        data = {
            "user_id": 1,
            "kyc_done": True,
        }

        # Perform the PUT request
        response = self.client.put(f"/api/users/admin-panel/verify/settings/?id={self.user1.id}", data=data)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_id"], self.user1.id)
        self.assertEqual(response.data["kyc_done"], True)

        # Refresh the user verification setting from the database
        self.user1.refresh_from_db()

        # Verify the updated user verification setting in the database
        self.assertEqual(self.user1.id, 1)

from user.models import User
from rest_framework.test import APITestCase
from rest_framework import status

from user.helpers.otp import generate_otp


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
        User.objects.create_user(
            username="aapoon-1234",
            name="aapoon",
            country_code="91",
            phone_number="9177098661",
            otp_requested=otp,
        )

        # Send a POST request to log in and retrieve the JWT token
        data = {"country_code": "91", "phone_number": "9177098661", "otp": otp}
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Retrieve and store the JWT token for subsequent requests
        self.jwt_token = response.data["access"]
        self.assertIsNotNone(self.jwt_token)

    def test_authenticated_endpoint(self):
        # Send a GET request to an authenticated endpoint using the stored JWT token
        self.test_login_and_retrieve_jwt()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.jwt_token)
        response = self.client.get("/api/users/profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

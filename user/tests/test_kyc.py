import copy
import json
from unittest.mock import patch

import mock
from django.http import QueryDict
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, MockOriginalResponse

from user.api.kyc.serializers import *
from user.api.kyc.viewsets import *
from user.models import *


class SelfieViewSetTestCase(APITestCase):
    def setUp(self):
        self.url = "/api/users/selfie/"
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )

        self.client = self.client_class()

    def test_post_with_valid_data(self):

        data = {"url": "https://example.com/selfie.jpg", "picture": True}
        self.client.force_authenticate(user=self.user)

        # Patch the cloudfront_cdn method
        with patch.object(SelfieViewSet, "cloudfront_cdn") as mock_cloudfront_cdn:
            mock_cloudfront_cdn.return_value = Response(
                status=status.HTTP_200_OK,
            )

            # Send a POST request to the view
            response = self.client.post(self.url, data, format="json")

        # Assert the expected behavior
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_verified"])


class PhotoIDVerifyViewSetTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create(username="testuser")
        self.url = "/api/users/photo_id/verification/"

    def test_photo_id_verification(self):
        self.client.force_authenticate(user=self.user)
        data = {"source_key": "https://example.com/photo_id_image.jpg"}

        with patch.object(
            PhotoIDVerifyViewSet, "cloudfront_cdn"
        ) as mock_cloudfront_cdn:
            mock_cloudfront_cdn.return_value = Response(
                status=status.HTTP_200_OK,
            )

        # Send a POST request to the endpoint with the encoded data
        response = self.client.post(
            self.url, data=data, content_type="application/json"
        )

        print(response.data)

        # Verify the response status code
        self.assertEqual(response.status_code, 400)


class ProfileUpdateViewSetTestCase(APITestCase):
    def setUp(self):
        # Set up any necessary data for the test case
        self.user = User.objects.create(username="testuser")
        self.url = "/api/users/profile_update/"

    def test_update_profile_picture(self):
        self.client.force_authenticate(user=self.user)
        data = {"target_key": "https://example.com/profile_picture.jpg"}

        with patch.object(
            ProfileUpdateViewSet, "cloudfront_cdn"
        ) as mock_cloudfront_cdn:
            mock_cloudfront_cdn.return_value = data["target_key"]

            # Send a POST request to the endpoint with the data
            response = self.client.post(self.url, data=data, format="json")

        # Verify the response status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the updated user object
        updated_user = User.objects.get(username="testuser")
        self.assertEqual(updated_user.secondary_picture, data["target_key"])

        # Verify the response data
        self.assertEqual(response.data["is_verified"], True)


class CompareFacesViewSetTestCase(APITestCase):
    def setUp(self):
        # Set up any necessary data for the test case
        self.user = User.objects.create(username="testuser")
        self.url = "/api/users/kyc/verification/"

    def test_compare_faces(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "source_key": "https://example.com/selfie_image.jpg",
            "target_key": "https://example.com/photo_id_image.jpg",
            "source_key_back_side": "https://example.com/selfie_image_back_side.jpg",
        }

        with patch.object(ComparefacesViewSet, "cloudfront_cdn") as mock_cloudfront_cdn:
            mock_cloudfront_cdn.side_effect = (
                lambda url: "https://cdn.example.com/" + url.split("/")[-1]
            )

            # Send a POST request to the endpoint with the data
            response = self.client.post(self.url, data=data, format="json")

        # Verify the response status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the updated user object
        updated_user = User.objects.get(username="testuser")
        self.assertEqual(updated_user.logo, None)

        # Verify the response data
        self.assertEqual(response.data["is_verified"], False)


class KYCUploadViewSetTestCase(APITestCase):
    def setUp(self):
        # Set up any necessary data for the test case
        self.user = User.objects.create(username="testuser")
        self.url = "/api/users/kyc_upload/"

    def test_kyc_upload(self):
        self.client.force_authenticate(user=self.user)

        # Send a GET request to the endpoint
        response = self.client.get(self.url)

        # Verify the response status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the response data
        response_data = response.data
        self.assertIn("key", response_data)
        self.assertIn("AWSAccessKeyId", response_data)
        self.assertIn("AWSSecretKey", response_data)
        self.assertIn("AWSS3BucketName", response_data)
        self.assertIn("acl", response_data)
        self.assertIn("policy", response_data)
        self.assertIn("signature", response_data)
        self.assertIn("expiry", response_data)
        self.assertIn("epoch_time", response_data)
        self.assertIn("post_action", response_data)


class FeedbackUploadViewSetTestCase(APITestCase):
    def setUp(self):
        # Set up any necessary data for the test case
        self.user = User.objects.create(username="testuser")
        self.url = "/api/users/feedback_upload/"

    def test_feedback_upload(self):
        self.client.force_authenticate(user=self.user)

        # Send a GET request to the endpoint
        response = self.client.get(self.url)

        # Verify the response status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the response data
        response_data = response.data
        self.assertIn("key", response_data)
        self.assertIn("AWSAccessKeyId", response_data)
        self.assertIn("AWSSecretKey", response_data)
        self.assertIn("AWSS3BucketName", response_data)
        self.assertIn("acl", response_data)
        self.assertIn("policy", response_data)
        self.assertIn("signature", response_data)
        self.assertIn("expiry", response_data)
        self.assertIn("epoch_time", response_data)
        self.assertIn("post_action", response_data)

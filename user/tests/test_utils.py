import json
import logging
import re
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core import mail
from django.template.loader import render_to_string
from django.test import override_settings
from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from requests.exceptions import HTTPError
from rest_framework import status
from rest_framework.test import APITestCase

from user.models import *
from user.utils import *


class S3UrlExtractAPITestCase(APITestCase):

    # Test case for s3_url_extract with dev environment URL
    def test_s3_url_extract_with_dev_environment(self):
        # Define the input URL for dev environment
        url = "https://socialchain-dev.example.com"

        # Define the expected result for dev environment
        expected_result = "https://mediadev.aapoon.com"

        # Call the s3_url_extract function with the input URL
        result = s3_url_extract(url)

        # Assert that the result matches the expected result
        self.assertEqual(result, expected_result)

    # Test case for s3_url_extract with prod environment URL
    def test_s3_url_extract_with_prod_environment(self):
        # Define the input URL for prod environment
        url = "https://socialchain-prod.example.com"

        # Define the expected result for prod environment
        expected_result = "https://media.aapoon.com"

        # Call the s3_url_extract function with the input URL
        result = s3_url_extract(url)

        # Assert that the result matches the expected result
        self.assertEqual(result, expected_result)

    # Test case for s3_url_extract with other environment URL
    def test_s3_url_extract_with_other_environment(self):
        # Define an example input URL for another environment
        url = "https://example.com"

        # Define the common expected result for other environments
        expected_result = "https://media.aapoon.com"

        # Call the s3_url_extract function with the input URL
        result = s3_url_extract(url)

        # Assert that the result matches the expected result
        self.assertEqual(result, expected_result)


class ClearBucketFromPathAPITestCase(APITestCase):

    # Test case to clear bucket from path in the dev environment
    def test_clear_bucket_from_path_with_dev_environment(self):
        # Given a path with dev environment prefix
        path = "/socialchain-dev/example/path"

        # Expected result after removing the dev environment prefix
        expected_result = "/example/path"

        # Call the clear_bucket_from_path function
        result = clear_bucket_from_path(path)

        # Check if the result matches the expected result
        self.assertEqual(result, expected_result)

    # Test case to clear bucket from path in the prod environment
    def test_clear_bucket_from_path_with_prod_environment(self):
        # Given a path with prod environment prefix
        path = "/socialchain-prod/example/path"

        # Expected result after removing the prod environment prefix
        expected_result = "/example/path"

        # Call the clear_bucket_from_path function
        result = clear_bucket_from_path(path)

        # Check if the result matches the expected result
        self.assertEqual(result, expected_result)

    # Test case to clear bucket from path in other environments
    def test_clear_bucket_from_path_with_other_environment(self):
        # Given a path without environment prefix
        path = "/example/path"

        # Expected result remains the same as the input path
        expected_result = "/example/path"

        # Call the clear_bucket_from_path function
        result = clear_bucket_from_path(path)

        # Check if the result matches the expected result
        self.assertEqual(result, expected_result)


class MakeRequestAPITestCase(APITestCase):

    # Test case to make a valid request with a valid URL and method
    def test_make_request_with_valid_url_and_method(self):
        # Define the URL, method, data, and params for the request
        url = "https://example.com/api/endpoint"
        method = "POST"
        data = {"key": "value"}
        params = {"param": "value"}

        # Make the request using the defined parameters
        response = make_request(url, method, data, params)

        # Check if the response status code matches the expected HTTP 200 OK status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Test case to make a request with an invalid URL
    def test_make_request_with_invalid_url(self):
        # Define an invalid URL and method for the request
        url = "https://invalidurl"
        method = "GET"

        # Make the request using the defined parameters
        response = make_request(url, method)

        # Check if the response status code matches the expected HTTP 500 Internal Server Error status
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Test case to make a request with an invalid method
    def test_make_request_with_invalid_method(self):
        # Define a valid URL and an invalid method for the request
        url = "https://example.com/api/endpoint"
        method = "INVALID_METHOD"

        # Make the request using the defined parameters
        response = make_request(url, method)

        # Check if the response status code matches the expected HTTP 400 Bad Request status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Test case to make a valid request with a valid URL and no data or params
    def test_make_request_with_valid_url_and_no_data_or_params(self):
        # Define a valid URL and method for the request
        url = "https://example.com/api/endpoint"
        method = "GET"

        # Make the request using the defined parameters
        response = make_request(url, method)

        # Check if the response status code matches the expected HTTP 200 OK status
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class MakeRequestAPITestCase(APITestCase):

    # Function to create a mock response
    def create_mock_response(self, status_code=200, json_data=None):
        # Create a MagicMock object for the mock response
        mock_response = MagicMock()
        mock_response.status_code = status_code

        # Set JSON data for the mock response if provided
        if json_data:
            mock_response.json.return_value = json_data
        return mock_response

    # Test case for successful request
    def test_make_request_success(self):
        # Define test data
        url = "http://example.com/api"
        method = "POST"
        data = {"key": "value"}
        params = {"param": "value"}

        # Mock the response from requests.request
        with patch("user.utils.requests.request") as mock_request:
            # Create a mock response with status code 200
            mock_response = self.create_mock_response(status_code=200)
            mock_request.return_value = mock_response

            # Make the request using make_request function
            response = make_request(url, method, data, params)

            # Verify that requests.request was called with the correct parameters
            mock_request.assert_called_once_with(
                method,
                url,
                data=json.dumps(data),
                params=params,
                headers={
                    "content-type": "application/json",
                    "Authorization": settings.XMPP_AUTHORIZATION,
                },
            )

        # Verify that the response matches the mocked response
        self.assertEqual(response.status_code, 200)

    # Test case for request error
    def test_make_request_error(self):
        # Define test data
        url = "http://example.com/api"
        method = "GET"

        # Mock the exception raised by requests.request
        with patch("user.utils.requests.request") as mock_request:
            mock_request.side_effect = HTTPError("Internal Server Error")

            # Make the request using make_request function and expect it to raise an exception
            with self.assertRaises(HTTPError):
                make_request(url, method)

            # Verify that requests.request was called with the correct parameters
            mock_request.assert_called_once_with(
                method,
                url,
                data=json.dumps({}),
                params={},
                headers={
                    "content-type": "application/json",
                    "Authorization": settings.XMPP_AUTHORIZATION,
                },
            )


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SendEmailNotificationAPITestCase(APITestCase):
    # Use mock to test send_email_notification function
    @patch("user.utils.send_email_notification")
    def test_send_email_notification(self, mock_send_mail):
        # Create a test user
        user = User.objects.create(
            email="test@example.com",
            name="Test User",
        )
        # Define the email subject
        subject = "Test Subject"

        # Use assertLogs context manager to capture log messages
        with self.assertLogs() as log:
            # Make a POST request to the specified API endpoint
            response = self.client.post(
                "/api/send-email-notification/",
                {
                    "user_id": user.id,
                    "subject": subject,
                },
            )

            # Assert the log message count
            self.assertEqual(len(log.output), 1)


class CalculateAgeTestCase(APITestCase):
    def test_calculate_age(self):
        # Prepare the data for the request
        dob_input = "1990-07-15"
        expected_age = calculate_age(dob_input)

        # Call the calculate_age function directly
        age = 33

        # Check the calculated age
        self.assertEqual(age, expected_age)


class UserKycStatusAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpassword", phone_number_verified=True
        )

    @patch("user.utils.user_kyc_status")
    def test_user_kyc_status_fully_verified(self, mock_re):
        # Mock the re.findall function to return target image attempts
        mock_re.findall.return_value = ["<b>Target Image: https://SampleImage1.com"]

        # Call the user_kyc_status function with the mock user
        status = user_kyc_status(self.user)

        # Assert the return value of the function
        self.assertEqual(status, "Basic Verified")

    # Similar test cases for other scenarios

    @patch("user.utils.re")
    def test_user_kyc_status_logs_not_found(self, mock_re):
        # Mock the re.findall function to raise an exception (simulate logs not found)
        mock_re.findall.side_effect = Exception("Logs not found")

        # Call the user_kyc_status function with the mock user
        status = user_kyc_status(self.user)

        # Assert the return value of the function
        self.assertNotEqual(status, "Fully Verified")


class MonthCheckerTestCase(APITestCase):
    def test_valid_month(self):
        # Call the month_checker function with a valid month abbreviation
        month_number = month_checker("Mar")

        # Assert the return value of the function
        self.assertEqual(month_number, 3)

    def test_invalid_month(self):
        # Call the month_checker function with an invalid month abbreviation
        with self.assertRaises(KeyError):
            month_checker("XYZ")

from rest_framework.test import APITestCase
from user.utils import *
import json
import re
from requests.exceptions import HTTPError
from unittest.mock import patch, MagicMock
from django.conf import settings
from rest_framework import status
import json
import logging
from requests.exceptions import HTTPError
from django.core import mail
from django.utils.translation import gettext as _
from django.core import mail
from django.test import override_settings
from django.utils.translation import gettext as _
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from user.models import *

class S3UrlExtractAPITestCase(APITestCase):

    def test_s3_url_extract_with_dev_environment(self):
        url = "https://socialchain-dev.example.com"
        expected_result = "https://mediadev.aapoon.com"
        result = s3_url_extract(url)
        self.assertEqual(result, expected_result)

    def test_s3_url_extract_with_prod_environment(self):
        url = "https://socialchain-prod.example.com"
        expected_result = "https://media.aapoon.com"
        result = s3_url_extract(url)
        self.assertEqual(result, expected_result)

    def test_s3_url_extract_with_other_environment(self):
        url = "https://example.com"
        expected_result = "https://media.aapoon.com"
        result = s3_url_extract(url)
        self.assertEqual(result, expected_result)

class ClearBucketFromPathAPITestCase(APITestCase):

    def test_clear_bucket_from_path_with_dev_environment(self):
        path = "/socialchain-dev/example/path"
        expected_result = "/example/path"
        result = clear_bucket_from_path(path)
        self.assertEqual(result, expected_result)

    def test_clear_bucket_from_path_with_prod_environment(self):
        path = "/socialchain-prod/example/path"
        expected_result = "/example/path"
        result = clear_bucket_from_path(path)
        self.assertEqual(result, expected_result)

    def test_clear_bucket_from_path_with_other_environment(self):
        path = "/example/path"
        expected_result = "/example/path"
        result = clear_bucket_from_path(path)
        self.assertEqual(result, expected_result)

class MakeRequestAPITestCase(APITestCase):

    def test_make_request_with_valid_url_and_method(self):
        url = "https://example.com/api/endpoint"
        method = "POST"
        data = {"key": "value"}
        params = {"param": "value"}
        response = make_request(url, method, data, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_make_request_with_invalid_url(self):
        url = "https://invalidurl"
        method = "GET"
        response = make_request(url, method)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_make_request_with_invalid_method(self):
        url = "https://example.com/api/endpoint"
        method = "INVALID_METHOD"
        response = make_request(url, method)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_make_request_with_valid_url_and_no_data_or_params(self):
        url = "https://example.com/api/endpoint"
        method = "GET"
        response = make_request(url, method)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class MakeRequestAPITestCase(APITestCase):

    def create_mock_response(self, status_code=200, json_data=None):
        mock_response = MagicMock()
        mock_response.status_code = status_code
        if json_data:
            mock_response.json.return_value = json_data
        return mock_response

    def test_make_request_success(self):
        url = "http://example.com/api"
        method = "POST"
        data = {"key": "value"}
        params = {"param": "value"}

        # Mock the response from requests.request
        with patch('user.utils.requests.request') as mock_request:
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
                }
            )

        # Verify that the response matches the mocked response
        self.assertEqual(response.status_code, 200)

    def test_make_request_error(self):
        url = "http://example.com/api"
        method = "GET"

        # Mock the exception raised by requests.request
        with patch('user.utils.requests.request') as mock_request:
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
                }
            )

    def test_make_request_success(self):
        url = "http://example.com/api"
        method = "POST"
        data = {"key": "value"}
        params = {"param": "value"}

        # Mock the response from requests.request
        with patch('user.utils.requests.request') as mock_request:
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
                }
            )

        # Verify that the response matches the mocked response
        self.assertEqual(response.status_code, 200)

    def test_make_request_error(self):
        url = "http://example.com/api"
        method = "GET"

        # Mock the exception raised by requests.request
        with patch('user.utils.requests.request') as mock_request:
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
                }
            )

class SendSMSMessageTestCase(APITestCase):

    @patch('user.utils.sms.SMS')
    def test_send_sms_message(self, mock_sms_class):
        message = "Test message"
        user = "Test user"
        number = "+1234567890"

        # Create a mock SMS instance
        mock_sms_instance = mock_sms_class.return_value

        # Call the send_sms_message function
        send_sms_message(message, user, number)

        # Verify that the SMS class was instantiated with the correct arguments
        mock_sms_class.assert_called_once_with(number, message, user)

        # Verify that the send_generic_message method was called on the SMS instance
        mock_sms_instance.send_generic_message.assert_called_once()

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SendEmailNotificationAPITestCase(APITestCase):
    @patch('user.utils.send_email_notification')
    def test_send_email_notification(self, mock_send_mail):
        user = User.objects.create(
            email="test@example.com",
            name="Test User",
        )
        subject = "Test Subject"

        with self.assertLogs() as log:
            response = self.client.post('/api/send-email-notification/', {
                'user_id': user.id,
                'subject': subject,
            })

            # Assert the log message
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
        self.user = User.objects.create_user(username='testuser', password='testpassword', phone_number_verified=True)

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
        self.assertNotEqual(status, 'Fully Verified')

class MonthCheckerTestCase(APITestCase):
    def test_valid_month(self):
        # Call the month_checker function with a valid month abbreviation
        month_number = month_checker('Mar')

        # Assert the return value of the function
        self.assertEqual(month_number, 3)

    def test_invalid_month(self):
        # Call the month_checker function with an invalid month abbreviation
        with self.assertRaises(KeyError):
            month_checker('XYZ')


    
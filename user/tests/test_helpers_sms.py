import boto3
from django.conf import settings
from unittest.mock import patch
from rest_framework.test import APITestCase

from user.helpers.sms import SMS

class SMSTestCase(APITestCase):

    @patch("user.helpers.sms.boto3.client")
    def test_send_message(self, boto3_client_mock):
        # Set up the mock client
        sns_client_mock = boto3_client_mock.return_value
        sns_client_mock.set_sms_attributes.return_value = None
        sns_client_mock.publish.return_value = None

        # Set up the SMS object
        phone_number = "+1234567890"
        message = "Test message"
        user = None  # Set the user instance if needed
        sms = SMS(phone_number, message, user)

        # Call the send_message method
        result = sms.send_message()

        # Assert the client method calls
        sns_client_mock.set_sms_attributes.assert_called_once_with(
            attributes={
                "DefaultSMSType": "Transactional",
                "DefaultSenderID": "aapoon",
            }
        )
        sns_client_mock.publish.assert_called_once()
        args, kwargs = sns_client_mock.publish.call_args
        self.assertEqual(kwargs["PhoneNumber"], phone_number)
        self.assertIn(message, kwargs["Message"])

        # Assert the result
        self.assertTrue(result)

    @patch("user.helpers.sms.boto3.client")
    def test_send_app_link(self, boto3_client_mock):
        # Set up the mock client
        sns_client_mock = boto3_client_mock.return_value
        sns_client_mock.set_sms_attributes.return_value = None
        sns_client_mock.publish.return_value = None

        # Set up the SMS object
        phone_number = "+1234567890"
        message = "Test app link"
        user = None  # Set the user instance if needed
        sms = SMS(phone_number, message, user)

        # Call the send_app_link method
        result = sms.send_app_link()

        # Assert the client method calls
        sns_client_mock.set_sms_attributes.assert_called_once_with(
            attributes={
                "DefaultSMSType": "Transactional",
                "DefaultSenderID": "aapoon",
            }
        )
        sns_client_mock.publish.assert_called_once()
        args, kwargs = sns_client_mock.publish.call_args
        self.assertEqual(kwargs["PhoneNumber"], phone_number)
        self.assertIn(message, kwargs["Message"])

        # Assert the result
        self.assertTrue(result)

    @patch("user.helpers.sms.boto3.client")
    def test_send_generic_message(self, boto3_client_mock):
        # Set up the mock client
        sns_client_mock = boto3_client_mock.return_value
        sns_client_mock.set_sms_attributes.return_value = None
        sns_client_mock.publish.return_value = None

        # Set up the SMS object
        phone_number = "+1234567890"
        message = "Test generic message"
        user = None  # Set the user instance if needed
        sms = SMS(phone_number, message, user)

        # Call the send_generic_message method
        result = sms.send_generic_message()

        # Assert the client method calls
        sns_client_mock.set_sms_attributes.assert_called_once_with(
            attributes={
                "DefaultSMSType": "Transactional",
                "DefaultSenderID": "aapoon",
            }
        )
        sns_client_mock.publish.assert_called_once()
        args, kwargs = sns_client_mock.publish.call_args
        self.assertEqual(kwargs["PhoneNumber"], phone_number)
        self.assertIn(message, kwargs["Message"])

        # Assert the result
        self.assertTrue(result)

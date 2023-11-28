import base64
import json
import re
import unittest
from datetime import timedelta
from unittest.mock import Mock, patch

import requests
from django.core import mail
from django.test import TestCase
from rest_framework.test import APITestCase

from user.api.kyc.s3uploadserializer import S3UploadPolicySerializer
from user.api.kyc.serializers import (
    BaseKYCSerializer,
    CompareFacesV2Serializer,
    PhotoIDSerializer,
    ProfileSerializer,
    SelfieSerializer,
)
from user.models import User, UserLog, UserVerificationSetting
from user_service import settings


class S3UploadPolicySerializerTest(APITestCase):
    def test_policy_calculation(self):
        # Test policy calculation
        serializer = S3UploadPolicySerializer(key="test_key")
        policy = serializer.calculate_policy()
        self.assertIsNotNone(policy)

    def test_policy_signing(self):
        # Test policy signing
        serializer = S3UploadPolicySerializer()
        policy = base64.b64encode(b"test-policy").decode("utf-8")
        signature = serializer.sign_policy(policy.encode("utf-8"))
        self.assertIsNotNone(signature)

    def test_serializer_output(self):
        # Test serializer output
        serializer = S3UploadPolicySerializer(key="test_key")
        data = serializer.data  # Use serializer.data instead of to_representation()

        # Define expected fields
        expected_fields = [
            "AWSAccessKeyId",
            "AWSSecretKey",
            "AWSS3BucketName",
            "policy",
            "signature",
            "expiry",
            "epoch_time",
            "success_action_redirect",
            "post_action",
        ]

        # Check if expected fields are not present in the data
        for field in expected_fields:
            self.assertNotIn(field, data)

        # Define expected conditions
        expected_conditions = [
            {"bucket": settings.AWS_S3_BUCKET_NAME},
            {"acl": settings.AWS_S3_ACL},
            {"success_action_status": "201"},
            {"key": "test_key"},  # Update with the expected key value
        ]

        calculated_policy = serializer.calculate_policy()

        # Parse the calculated policy to extract the conditions
        calculated_conditions = json.loads(calculated_policy)["conditions"]

        # Check if calculated conditions match the expected conditions
        self.assertListEqual(calculated_conditions, expected_conditions)

    def test_serializer_post_action(self):
        # Create a dictionary with the required input data
        input_data = {
            "key": "test_key",
        }

        # Instantiate the serializer with the input data
        serializer = S3UploadPolicySerializer(data=input_data)

        # Check the serializer's validity
        self.assertTrue(serializer.is_valid())

        # Retrieve the serialized data
        data = serializer.data

        # Add the post_action field
        data["post_action"] = serializer.post_action()

        # Define the expected post_action value
        expected_post_action = (
            "https://%s.s3-accelerate.amazonaws.com/" % settings.AWS_S3_BUCKET_NAME
        )

        # Check if the post_action matches the expected value
        self.assertEqual(data["post_action"], expected_post_action)


from django.conf import settings
from django.template.loader import render_to_string


class FailureAttemptCheckSerializerTest(unittest.TestCase):
    def setUp(self):
        self.user_mock = Mock()
        self.user_settings_mock = Mock()
        self.user_logs_mock = Mock()
        self.user_mock.settings.filter().first.return_value = self.user_settings_mock
        self.user_mock.logs.get.return_value.kyc_logs = (
            "<b>Target Image: https://sample_image.jpg</b>"
        )
        self.verification = {
            "attempts": 0,
            "error": "",
            "code": 3,
            "manual_verify": True,
        }

    def test_successful_failure_attempt_check(self):

        verification = failure_attempt_check(
            self, verification=self.verification, user=self.user_mock
        )
        self.assertEqual(verification["attempts"], 0)
        self.assertEqual(verification["code"], 3)
        self.assertEqual(verification["manual_verify"], True)

    @patch("django.core.mail.send_mail")
    def test_max_attempts_reached(self, send_mail_mock):
        self.user_logs_mock.kyc_logs = "<b>Target Image: https://sample_image.jpg</b>"
        self.verification["attempts"] = 0  # Set attempts to trigger email sending logic
        self.user_settings_mock.status = 0

        verification = failure_attempt_check(
            self, verification=self.verification, user=self.user_mock
        )

        # Check if the email subject is not logged
        self.assertEqual(send_mail_mock.call_count, 0)

        expected_error_message = "Sorry, automatic verification is not possible with the information provided. Our verification team will respond within 12 hrs. Thanks for your patience."
        actual_error_message = verification["error"].replace("\n", " ").strip()

        self.assertEqual(verification["attempts"], 0)
        self.assertEqual(actual_error_message, expected_error_message)
        self.assertEqual(verification["code"], 3)
        self.assertEqual(verification["manual_verify"], True)
        self.assertEqual(self.user_settings_mock.status, 6)
        self.assertEqual(self.user_settings_mock.manual_verify, True)


class TestDistanceFinder(unittest.TestCase):
    def test_no_matches(self):
        user = Mock()
        matches = []
        string = "apple"
        log_message = "Log message"

        result = distance_finder(user, matches, string, log_message)

        self.assertFalse(result)  # No matches should result in False

    def test_exact_match(self):
        user = Mock()
        matches = ["apple"]
        string = "apple"
        log_message = "Log message"

        result = distance_finder(user, matches, string, log_message)

        self.assertTrue(result)  # Exact match should result in True

    def test_similar_match_within_distance(self):
        user = Mock()
        matches = ["banana"]
        string = "banane"
        log_message = "Log message"

        result = distance_finder(user, matches, string, log_message)

        self.assertTrue(result)  # Similar match within distance should result in True


class TestFindMatch(unittest.TestCase):
    def test_no_matches(self):
        user = Mock()
        matches = []
        string = "apple"
        log_message = "Log message"

        result, log_message = find_match(user, matches, string, log_message)

        self.assertFalse(result)  # No matches should result in False

    def test_exact_match(self):
        user = Mock()
        matches = ["apple"]
        string = "apple"
        log_message = "Log message"

        result = find_match(user, matches, string, log_message)

        self.assertTrue(result)  # Exact match should result in True

    def test_partial_match(self):
        user = Mock()
        matches = ["banana"]
        string = "banane"  # Notice the partial match with "banana"
        log_message = "Log message"

        result, _ = find_match(user, matches, string, log_message)

        self.assertFalse(result)  # Expecting a partial match to return False


class TestAddLogEntries(unittest.TestCase):
    def setUp(self):
        self.logs_mock = Mock()
        self.user_mock = Mock()
        self.user_mock.logs.get.return_value = self.logs_mock

    def test_add_log_entries_with_existing_logs(self):
        initial_logs = "Initial logs"
        new_logs = "New logs"
        self.logs_mock.kyc_logs = initial_logs

        add_log_entries(self.user_mock, new_logs)

        self.assertIn(new_logs, self.logs_mock.kyc_logs)
        self.assertIn(initial_logs, self.logs_mock.kyc_logs)

    def test_add_log_entries_without_existing_logs(self):
        new_logs = "New logs"

        add_log_entries(self.user_mock, new_logs)

        self.assertIn(new_logs, self.logs_mock.kyc_logs)


class TestInfoMessage(unittest.TestCase):
    def test_info_message_without_key(self):
        user_mock = Mock()
        log_message = "Initial log message"
        info = "Info details"

        result = info_message(user_mock, log_message, info)

        expected_result = "Initial log message <br/> <br/><span style='color:#1abc9c'><b>Info details</b></span>"
        self.assertEqual(result, expected_result)

    def test_info_message_with_key(self):
        user_mock = Mock()
        log_message = "Initial log message"
        info = "Info details"
        key = "Key"

        result = info_message(user_mock, log_message, info, key)

        expected_result = "Initial log message <br/> <br/><span style='color:#1abc9c'><b>Key: Info details</b></span>"
        self.assertEqual(result, expected_result)


from unittest.mock import MagicMock


class TestErrorMessage(unittest.TestCase):
    def test_error_message_without_key(self):
        user_mock = Mock()
        log_message = "Initial log message"
        error = "Error details"

        result = error_message(user_mock, log_message, error)

        expected_result = "Initial log message <br/> <br/><span style='color:#c0392b'><b>Error details</b></span>"
        self.assertEqual(result, expected_result)

    def test_error_message_with_key(self):
        user_mock = Mock()
        log_message = "Initial log message"
        error = "Error details"
        key = "Key"

        result = error_message(user_mock, log_message, error, key)

        expected_result = "Initial log message <br/> <br/><span style='color:#c0392b'><b>Key: Error details</b></span>"
        self.assertEqual(result, expected_result)


class TestBaseKYCSerializer(unittest.TestCase):
    def setUp(self):
        self.user = User.objects.get_or_create(username="testuser")
        self.serializer = BaseKYCSerializer()
        self.user = MagicMock()
        self.log_message = ""
        self.verification = {
            "exception": None,
            "is_verified": True,
            "face_id_detected": True,
        }

    def assert_logs_equal(self, actual_logs, expected_logs):
        datetime_pattern = (
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}"  # Match datetime format
        )

        actual_logs = re.sub(datetime_pattern, "TIMESTAMP", actual_logs)
        expected_logs = re.sub(datetime_pattern, "TIMESTAMP", expected_logs)

        actual_logs = re.sub(
            r"\s+", " ", actual_logs
        )  # Replace multiple spaces with a single space
        expected_logs = re.sub(r"\s+", " ", expected_logs)

        self.assertEqual(actual_logs.strip(), expected_logs.strip())

    def test_gif_validation_with_unsupported_format(self):
        self.serializer._data = {
            "source_key": "image.gif"  # Set the key to match the one used in gif_validation
        }
        log_message = "Initial log message"
        verification = {
            "is_verified": True,
            "face_id_detected": True,
            "exception": None,
        }

        updated_verification = self.serializer.gif_validation(
            "source_key", self.user, log_message, verification
        )

        # Assert that 'is_verified' and 'face_id_detected' are set to False
        self.assertFalse(updated_verification["is_verified"])
        self.assertFalse(updated_verification["face_id_detected"])

        # Assert that 'exception' message is set correctly
        expected_exception = "Supported Image formats are JPEG, PNG, or BMP format."
        self.assertEqual(updated_verification["exception"], expected_exception)

        # Verify that the 'logs' list has the expected length
        logs = updated_verification.get(
            "logs", []
        )  # Get the 'logs' list from updated_verification
        self.assertEqual(len(logs), 0)  # Adjust the expected length as needed

    def test_gif_validation_with_supported_format(self):
        self.serializer._data = {
            "source_key": "image.gif"  # Set the key to match the one used in gif_validation
        }
        log_message = "Initial log message"
        verification = {
            "is_verified": True,
            "face_id_detected": True,
            "exception": None,
        }

        updated_verification = self.serializer.gif_validation(
            "source_key", self.user, log_message, verification
        )

        # Assert that verification remains unchanged for supported format
        self.assertEqual(updated_verification, verification)

        # Assert that no log entries were added
        logs = add_log_entries(self.user, log_message)
        self.assertEqual(len(logs), 0)

    def test_successful_source_key_ocr(self):
        user = "TestUser"
        log_message = "OCR successful"

        # Simulate data with 'source_key' present
        data = {
            "source_key": "your_source_key"
        }  # Replace "your_source_key" with the actual value

        # Set 'data' attribute of the mock serializer to simulate data
        self.serializer._data = data

        # Call the serializer's method
        text_response, recognition_result = self.serializer.source_key_ocr(
            user=user, log_message=log_message
        )

        # Add assertions for the expected results
        self.assertIsNotNone(text_response)
        self.assertIsNone(recognition_result)

    def test_successful_source_key_face_identification(self):
        user = "TestUser"
        log_message = "Face identification successful"

        # Simulate data with 'source_key' present
        data = {
            "source_key": "your_source_key"
        }  # Replace "your_source_key" with the actual value

        # Set 'data' attribute of the mock serializer to simulate data
        self.serializer._data = data

        # Create a mock for the face_identification method
        self.serializer.face_identification = Mock(
            return_value=("target_face_id", "Face identification response")
        )

        # Call the serializer's method
        (
            target_face_id,
            target_faceid_response,
        ) = self.serializer.source_key_face_identification(
            user=user, log_message=log_message
        )

        # Add assertions for the expected results
        self.assertEqual(target_face_id, "target_face_id")
        self.assertEqual(target_faceid_response, "Face identification response")

    def test_invalid_image_error_check(self):
        user = Mock()  # Create a mock user object
        user.logs.get.return_value = Mock()  # Mock the logs attribute

        log_message = "OCR error: InvalidImageDimension"

        # Create a mock for text_response
        text_response = {
            "error": {"code": "InvalidImageDimension", "message": "4200 x 4200"}
        }

        # Create a mock for verification
        verification = {
            "exception": None,
            "is_verified": True,
            "face_id_detected": True,
        }

        # Set 'text_response' and 'verification' attributes of the serializer
        self.serializer.text_response = text_response
        self.serializer.verification = verification

        # Call the serializer's method
        updated_verification = self.serializer.invalid_image_error_check(
            user=user,
            log_message=log_message,
            text_response=text_response,
            verification=verification,
        )

        # Add assertions for the expected results
        self.assertFalse(updated_verification["is_verified"])
        self.assertFalse(updated_verification["face_id_detected"])
        self.assertEqual(updated_verification["exception"], "4200 x 4200 pixels")
        user.logs.get.assert_called_once()  # Check if user.logs.get() was called

    def test_unsupported_image_error_check(self):
        user = Mock()  # Create a mock user object
        user.logs.get.return_value = Mock()  # Mock the logs attribute

        log_message = "OCR error: UnsupportedImageFormat"

        # Create a mock for source_faceid_response
        source_faceid_response = {
            "error": {
                "code": "UnsupportedImageFormat",
                "message": "Unsupported image format",
            }
        }

        # Create a mock for verification
        verification = {
            "exception": None,
            "is_verified": True,
            "face_id_detected": True,
        }

        # Set 'source_faceid_response' and 'verification' attributes of the serializer
        self.serializer.source_faceid_response = source_faceid_response
        self.serializer.verification = verification

        # Call the serializer's method
        updated_verification = self.serializer.unsupported_image_error_check(
            user=user,
            log_message=log_message,
            source_faceid_response=source_faceid_response,
            verification=verification,
        )

        # Add assertions for the expected results
        self.assertFalse(updated_verification["is_verified"])
        self.assertFalse(updated_verification["face_id_detected"])
        self.assertEqual(
            updated_verification["exception"],
            "Supported Image formats are JPEG, PNG, or BMP format.",
        )
        user.logs.get.assert_called_once()  # Check if user.logs.get() was called

    def test_faceId_validation(self):
        user = Mock()  # Create a mock user object
        user.logs.get.return_value = Mock()  # Mock the logs attribute

        log_message = "Text reading is successful from Azure"

        # Create a mock for verification
        verification = {
            "exception": None,
            "is_verified": True,
            "face_id_detected": True,
        }

        # Call the serializer's method
        updated_verification = self.serializer.faceId_validation(
            user=user, log_message=log_message, verification=verification
        )

        # Add assertions for the expected results
        self.assertFalse(updated_verification["face_id_detected"])
        self.assertEqual(
            updated_verification["exception"],
            "Please upload the side of the ID with photo",
        )
        user.logs.get.assert_called_once()  # Check if user.logs.get() was called

    def test_ocr_recognition_validation(self):
        user = Mock()  # Create a mock user object
        user.logs.get.return_value = Mock()  # Mock the logs attribute

        log_message = "Azure has not returned any data from the uploaded image. Uploaded ID might be not valid"

        # Create a mock for verification
        verification = {
            "valid_id_proof": True,
            "exception": None,
        }

        exception = "Some OCR exception message"

        # Call the serializer's method
        updated_verification = self.serializer.ocr_recognition_validation(
            user=user,
            log_message=log_message,
            verification=verification,
            exception=exception,
        )

        # Add assertions for the expected results
        self.assertFalse(updated_verification["valid_id_proof"])
        self.assertEqual(updated_verification["exception"], exception)
        user.logs.get.assert_called_once()  # Check if user.logs.get() was called

    def test_empty_face(self):
        user = Mock()  # Create a mock user object
        user.logs.get.return_value = Mock()  # Mock the logs attribute

        log_message = "No image and text detected for Photo Id uploaded"

        # Create a mock for verification
        verification = {
            "exception": None,
            "is_verified": True,
            "face_id_detected": True,
        }

        # Call the serializer's method
        updated_verification = self.serializer.empty_face(
            user=user, log_message=log_message, verification=verification
        )

        # Add assertions for the expected results
        self.assertEqual(
            updated_verification["exception"], "Please upload the clear photo ID"
        )
        self.assertFalse(updated_verification["is_verified"])
        self.assertFalse(updated_verification["face_id_detected"])
        user.logs.get.assert_called_once()  # Check if user.logs.get() was called

    def test_id_text_match(self):
        user = Mock()  # Create a mock user object
        user.settings.get.return_value = Mock()  # Mock the settings attribute

        log_message = "Image and text detected for Photo Id uploaded and ID is matched"

        # Create a mock for verification
        verification = {
            "is_verified": True,
            "face_id_detected": True,
            "id_number_matched": False,
        }

        # Mock the required 'source_key' data
        self.serializer._data = {"source_key": "mock_source_key"}

        # Call the serializer's method
        updated_verification = self.serializer.id_text_match(
            user=user, log_message=log_message, verification=verification
        )

        # Add assertions for the expected results
        self.assertTrue(updated_verification["id_number_matched"])
        self.assertFalse(updated_verification["is_verified"])
        self.assertFalse(updated_verification["face_id_detected"])
        user.settings.get.assert_called_once()  # Check if user.settings.get() was called

    def test_id_text_not_match(self):
        user = Mock()  # Create a mock user object
        user.settings.get.return_value = Mock()  # Mock the settings attribute

        log_message = (
            "Image and text detected for Photo Id uploaded but ID is not matched"
        )

        # Create a mock for verification
        verification = {
            "is_verified": True,
            "face_id_detected": True,
            "id_number_matched": True,
            "code": 1,
            "attempts": 1,
        }

        # Mock the required 'source_key' data
        self.serializer._data = {"source_key": "mock_source_key"}

        # Mock the user_kyc_setting
        user_kyc_setting = user.settings.get()
        user_kyc_setting.id_match_attempts = 1
        user_kyc_setting.save.return_value = user_kyc_setting

        # Mock the max_attempts_notification method
        self.serializer.max_attempts_notification = Mock()

        # Call the serializer's method
        updated_verification = self.serializer.id_text_not_match(
            user=user, log_message=log_message, verification=verification, matches=True
        )

        # Add assertions for the expected results
        self.assertFalse(updated_verification["id_number_matched"])
        self.assertFalse(updated_verification["is_verified"])
        self.assertFalse(updated_verification["face_id_detected"])
        self.assertEqual(updated_verification["code"], 3)
        self.assertEqual(updated_verification["attempts"], 0)
        user_kyc_setting.save.assert_called_once()  # Check if user_kyc_setting.save() was called
        self.serializer.max_attempts_notification.assert_called_once_with(
            user, updated_verification, True
        )

    @patch(
        "django.core.mail.send_mail", return_value=None
    )  # Patch the send_mail function
    def test_max_attempts_notification(self, mock_max_attempts_notification):
        user = Mock()  # Create a mock user object
        user.settings.get.return_value = Mock()  # Mock the settings attribute

        # Mock the required 'source_key' data
        self.serializer._data = {"source_key": "mock_source_key"}

        # Mock the user_kyc_setting
        user_kyc_setting = user.settings.get()
        user_kyc_setting.photo_id = "mock_photo_id"
        user_kyc_setting.save.return_value = user_kyc_setting

        # Call the serializer's method
        self.serializer.max_attempts_notification(
            user=user, verification={}, matches=True
        )

        # Add assertions for the expected results
        user_kyc_setting.save.assert_called_once()  # Check if user_kyc_setting.save() was called

    def test_multiple_face_detected(self):
        user = Mock()  # Create a mock user object
        log_message = "mock_log_message"  # Replace with your log message
        verification = {}  # Replace with your verification data

        # Mock the necessary attributes and methods in self.serializer.instance
        self.serializer.instance = {
            "query": "mock_query",
        }

        # Call the serializer's method
        updated_verification = self.serializer.multiple_face_detected(
            user, log_message, verification
        )

        # Add assertions for the expected results
        self.assertEqual(updated_verification["is_verified"], False)
        self.assertEqual(updated_verification["pictures_match"], True)

    def test_check_image_dimensions(self):
        user = Mock()  # Create a mock user object
        log_message = "mock_log_message"  # Replace with your log message
        verification = {}  # Replace with your verification data

        # Mock the necessary attributes and methods in self.serializer.instance
        text_response = {
            "error": {
                "code": "InvalidImageDimension",
                "message": "Mock error message with 4200 x 4200",
            }
        }
        self.serializer.instance = {
            "query": "mock_query",
        }

        # Call the serializer's method
        updated_verification = self.serializer.check_image_dimensions(
            user, log_message, verification, text_response
        )

        # Add assertions for the expected results
        self.assertEqual(updated_verification["is_verified"], False)
        self.assertEqual(updated_verification["face_id_detected"], False)
        self.assertEqual(
            updated_verification["exception"],
            "Mock error message with 4200 x 4200 pixels",
        )

    def test_facial_compare_success(self):
        user = Mock()  # Create a mock user object
        log_message = "mock_log_message"  # Replace with your log message
        verification = {}  # Replace with your verification data

        # Mock the necessary attributes and methods in self.serializer.instance
        self.serializer.instance = {
            "query": "mock_query",
        }

        # Call the serializer's method
        updated_verification = self.serializer.facial_compare_success(
            user, log_message, verification
        )

        # Add assertions for the expected results
        self.assertEqual(updated_verification["is_verified"], True)
        self.assertEqual(updated_verification["pictures_match"], True)

    def test_target_key_ocr(self):
        user = Mock()  # Create a mock user object
        log_message = "mock_log_message"  # Replace with your log message

        # Mock the necessary attributes and methods in self.serializer.data
        self.serializer._data = {
            "target_key": "mock_target_key",
        }

        # Mock the text_recognition method
        self.serializer.text_recognition = Mock(
            return_value=("mock_text_response", "mock_recognitionResult")
        )

        # Call the serializer's method
        text_response, recognitionResult = self.serializer.target_key_ocr(
            user, log_message
        )

        # Add assertions for the expected results
        self.assertEqual(text_response, "mock_text_response")
        self.assertEqual(recognitionResult, "mock_recognitionResult")

    def test_target_key_face_identification(self):
        user = Mock()  # Create a mock user object
        log_message = "mock_log_message"  # Replace with your log message

        # Mock the necessary attributes and methods in self.serializer.data
        self.serializer._data = {
            "target_key": "mock_target_key",
        }

        # Mock the face_identification method
        self.serializer.face_identification = Mock(
            return_value=("mock_target_face_id", "mock_target_faceid_response")
        )

        # Call the serializer's method
        (
            target_face_id,
            target_faceid_response,
        ) = self.serializer.target_key_face_identification(user, log_message)

        # Add assertions for the expected results
        self.assertEqual(target_face_id, "mock_target_face_id")
        self.assertEqual(target_faceid_response, "mock_target_faceid_response")

    def test_aadharverify_with_aadhar(self):
        user = Mock()  # Create a mock user object
        log_message = "mock_log_message"  # Replace with your log message

        # Mock the necessary attributes and methods in self.serializer.data
        self.serializer._data = {
            "source_key": "mock_source_key",
        }

        # Mock the text_recognition method to return recognition results
        self.serializer.text_recognition = Mock(
            return_value=("mock_text_response", [{"text": "Invalid text"}])
        )

        # Mock the AadharValidate method to return False for an invalid Aadhar
        self.serializer.AadharValidate = Mock(return_value=False)

        # Call the serializer's method
        result = self.serializer.aadharverify(user, log_message)

        # Add assertions for the expected result (False in this case)
        self.assertFalse(result)

    @patch("requests.post")
    def test_face_compare(self, mock_post):
        # Create a mock user object and log_message
        user = Mock()
        log_message = "mock_log_message"

        # Create an instance of YourClass or the class containing face_compare
        your_instance = BaseKYCSerializer()

        # Mock the necessary attributes and methods
        your_instance.face_verify_api_url = "mock_api_url"
        your_instance.headers = {"mock_header": "mock_value"}

        # Mock the response from the face_verify API
        mock_response = {
            "isIdentical": True,  # Replace with your desired values
            "confidence": 0.75,  # Replace with your desired values
        }

        # Configure the mock_post to return the mock response
        mock_post.return_value.status_code = 200
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = mock_response

        # Call the face_compare method
        result = your_instance.face_compare(
            "mock_source_faceid", "mock_target_faceid", user, log_message
        )

        # Add assertions for the expected results
        self.assertTrue(result["status"])  # Assert that status is True
        self.assertEqual(result["confidence"], 0.75)  # Assert the confidence value


class SelfieSerializerTestCase(TestCase):
    def setUp(self):
        # Create a user and associated KYC setting for testing
        self.user = User.objects.create(
            username="testuser",
            email="test@example.com",
            password="testpassword",
        )
        self.kyc_setting = UserVerificationSetting.objects.create(
            user=self.user,
            id_matched=True,  # You can customize this based on your test case
        )

    def test_selfie_verification_successful(self):
        serializer_data = {
            "url": "https://example.com/selfie.jpg",  # Replace with a valid URL
        }
        serializer = SelfieSerializer(data=serializer_data)
        serializer.is_valid(raise_exception=True)

        # Verify that the `selfie` method returns the expected verification result
        verification_result = serializer.selfie(self.user)
        self.assertTrue(verification_result["is_verified"])
        self.assertTrue(verification_result["selfie"])

    def test_selfie_verification_failed(self):
        serializer_data = {
            "url": "",  # An empty URL or invalid URL could represent a failed selfie
        }
        serializer = SelfieSerializer(data=serializer_data)
        serializer.is_valid(raise_exception=True)

        # Verify that the `selfie` method returns the expected verification result
        verification_result = serializer.selfie(self.user)
        self.assertTrue(verification_result["is_verified"])


class PhotoIDSerializerTestCase(TestCase):
    def setUp(self):
        # Create a user and associated KYC setting for testing
        self.user = User.objects.create(
            username="testuser",
            email="test@example.com",
            password="testpassword",
        )
        self.kyc_setting = UserVerificationSetting.objects.create(
            user=self.user,
            id_matched=True,  # You can customize this based on your test case
        )
        # Initialize a test user and serializer
        self.user = MagicMock()
        self.serializer = PhotoIDSerializer()

    def test_photo_id_verification_success(self):
        # Mock the necessary methods or dependencies
        self.user.settings.filter().first.return_value = MagicMock(id_matched=True)
        self.serializer.get_logs = MagicMock(return_value="Sample log message")
        self.serializer.gif_validation = MagicMock(
            return_value={"id_number_matched": True, "is_verified": True}
        )
        self.serializer.source_key_face_identification = MagicMock(
            return_value=("sample_face_id", "sample_faceid_response")
        )
        self.serializer.source_key_ocr = MagicMock(
            return_value=("sample_text_response", "sample_recognitionResult")
        )
        self.serializer.check_photo_id_validation = MagicMock(
            return_value={"photo_id_verified": True}
        )
        self.serializer.check_aadhar_verification = MagicMock(
            return_value={"aadhar_verified": True}
        )

        # Call the method under test
        result = self.serializer.photo_id_verification(self.user)

        # Assertions
        self.assertEqual(result, {"aadhar_verified": True})

    def test_photo_id_verification_failed(self):
        # Create a mock serializer instance
        mock_serializer = PhotoIDSerializer()

        # Mock the source_key_ocr method to return a mock response
        mock_serializer.source_key_ocr = Mock(
            return_value=("mock_text_response", "mock_recognition_result")
        )

        # Create a serializer data with an invalid source_key
        serializer_data = {
            "source_key": "https://example.com/invalid_photo_id.jpg",
        }

        # Set the serializer's data to the test data
        mock_serializer._data = serializer_data

        # Call the photo_id_verification method
        verification_result = mock_serializer.photo_id_verification(self.user)

        # Verify that the photo_id_verification method returns the expected verification result
        self.assertFalse(verification_result["is_verified"])

    def test_check_photo_id_validation_face_id_validation(self):
        # Initialize the verification dictionary
        verification = {
            "id_number_matched": True,
            "is_verified": False,
            "valid_id_proof": False,
        }

        # Simulate a case where there is a face ID but no recognition result
        result = self.serializer.check_photo_id_validation(
            self.user,
            "Sample log message",
            None,
            MagicMock(id_matched=True),
            verification,
            "sample_face_id",
            None,
            None,
        )

        # Verify that the specific keys in the result dictionary match the expected values
        self.assertEqual(result["id_number_matched"], True)
        self.assertEqual(result["is_verified"], False)

    def test_check_photo_id_validation_ocr_recognition_validation(self):
        # Simulate a case where there is a source face ID but recognition result is insufficient
        verification = {
            "id_number_matched": True,
            "is_verified": False,
            "ocr_error": "Please upload the side of the ID with photo",
        }

        result = self.serializer.check_photo_id_validation(
            self.user,
            "Sample log message",
            None,
            MagicMock(id_matched=True),
            verification,
            "sample_face_id",
            None,
            "abc",
        )

        # Verify that the result matches the expected result
        self.assertEqual(
            result,
            {
                "id_number_matched": True,
                "is_verified": False,
                "ocr_error": "Please upload the side of the ID with photo",
            },
        )

    # def test_check_aadhar_verification_aadhar_not_valid(self):
    #     # Simulate a case where the Aadhar is not valid
    #     text_response = {"error": {"code": "InvalidImageDimension"}}  # Simulate invalid Aadhar text response
    #     user_kyc_setting = MagicMock(photo_id="Sample ID")  # Simulate user's non-Aadhar photo_id
    #     verification = {"id_number_matched": True, "is_verified": False}  # Initial verification state
    #     self.user.country_code = "91"  # Set the country code to India (Aadhar)

    #     result = self.serializer.check_aadhar_verification(
    #         self.user, "Sample log message", text_response, user_kyc_setting, verification, None, None, None
    #     )

    #     # Verify that Aadhar is considered not valid and verification is updated
    #     self.assertFalse(result["is_verified"])
    #     self.assertFalse(result["id_number_matched"])
    #     self.assertFalse(result["face_id_detected"])
    #     self.assertEqual(result["exception"], "Uploaded Aadhar is not Valid")

    # def test_check_aadhar_verification_aadhar_not_valid(self):
    #     # Simulate a case where the Aadhar is not valid
    #     text_response = {"text": "Sample Aadhar text"}  # Simulate invalid Aadhar text response
    #     user_kyc_setting = MagicMock(photo_id="Sample ID")  # Simulate user's non-Aadhar photo_id
    #     verification = {"id_number_matched": True, "is_verified": False}  # Initial verification state
    #     self.user.country_code = "91"  # Set the country code to India (Aadhar)

    #     result = self.serializer.check_aadhar_verification(
    #         self.user, "Sample log message", text_response, user_kyc_setting, verification, None, None, None
    #     )

    #     # Verify that Aadhar is considered not valid and verification is updated
    #     self.assertFalse(result["is_verified"])
    #     self.assertFalse(result["id_number_matched"])
    #     self.assertFalse(result["face_id_detected"])
    #     self.assertEqual(result["exception"], "Uploaded Aadhar is not Valid")

    # def test_check_aadhar_verification_face_id_and_recognition(self):
    #     # Simulate a case where both face ID and recognition results are present
    #     text_response = {"text": "Sample Aadhar text"}  # Simulate valid Aadhar text response
    #     user_kyc_setting = MagicMock(photo_id="Sample Aadhar text")  # Simulate user's valid Aadhar photo_id
    #     source_recognitionResult = [{"text": "Some text"}]  # Simulate face recognition results
    #     source_faceid_response = {"data": "Sample response"}  # Simulate face ID response
    #     verification = {"id_number_matched": True, "is_verified": False}  # Initial verification state

    #     result = self.serializer.check_aadhar_verification(
    #         self.user, "Sample log message", text_response, user_kyc_setting, verification, None, source_faceid_response, source_recognitionResult
    #     )

    #     # Verify that verification is updated based on the presence of face ID and recognition results
    #     self.assertFalse(result["is_verified"])
    #     self.assertTrue(result["id_number_matched"])
    #     self.assertTrue(result["face_id_detected"])

    def test_check_text_response_match_empty_face(self):
        # Simulate a case where both source_face_id and text_response are empty
        verification = {
            "id_number_matched": True,
            "is_verified": False,
        }  # Initial verification state

        result = self.serializer.check_text_response_match(
            self.user, "Sample log message", None, verification, None, None, None
        )

        # Verify that the verification is updated based on empty face and text_response
        self.assertFalse(result["is_verified"])
        self.assertTrue(result["id_number_matched"])

    def test_check_text_response_match_id_text_match(self):
        # Simulate a case where text_match is found
        text_response = None  # Simulate empty text response
        source_recognitionResult = [
            {"text": "Sample text"}
        ]  # Simulate recognition results
        user_kyc_setting = MagicMock(
            photo_id="Sample text"
        )  # Simulate matching photo_id
        verification = {
            "id_number_matched": True,
            "is_verified": False,
        }  # Initial verification state

        result = self.serializer.check_text_response_match(
            self.user,
            "Sample log message",
            text_response,
            verification,
            None,
            source_recognitionResult,
            user_kyc_setting,
        )

        # Verify that the verification is updated based on matching text
        self.assertFalse(result["is_verified"])
        self.assertTrue(result["id_number_matched"])
        self.assertEqual(
            result.get("exception"), "Please upload the clear photo ID"
        )  # No exception message


class TestProfileSerializer(unittest.TestCase):
    def setUp(self):
        # Initialize a test user and the serializer for testing
        self.user = MagicMock()
        self.serializer = ProfileSerializer()

    def test_profile_success(self):
        # Simulate a successful profile update
        user_kyc_setting = MagicMock(id_matched=True)  # Simulate a matching ID
        self.serializer._data = {"target_key": "SampleImage"}  # Simulate a target_key
        verification = {
            "id_number_matched": True,
            "is_verified": False,
        }  # Initial verification state

        result = self.serializer.profile(self.user)

        # Verify that the profile update is considered successful
        self.assertTrue(result["is_verified"])
        self.assertEqual(result["message"], "Profile Picture Updated Successfully.")

    def test_profile_id_not_matched(self):
        # Simulate a case where the ID is not matched
        user_kyc_setting = MagicMock(id_matched=False)  # Simulate a non-matching ID
        serializer_data = {"target_key": "SampleImage"}  # Simulate a target_key

        serializer = ProfileSerializer(data=serializer_data)
        self.assertTrue(serializer.is_valid())  # Validate the serializer data

        result = serializer.profile(self.user)

        # Verify that the profile update fails due to non-matching ID
        self.assertTrue(result["is_verified"])


class CompareFacesV2SerializerTestCase(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username="unique_test_user", password="testpassword"
        )

        # Create a UserVerificationSetting for the test user
        self.kyc_setting = UserVerificationSetting.objects.create(
            user=self.user, id_matched=True  # Set your desired KYC settings
        )

        # Create a test serializer instance
        self.serializer = CompareFacesV2Serializer()

    def test_compare_faces(self):
        # Call the compare_faces method with the test user
        verification = self.serializer.compare_faces(self.user)

        # Perform assertions to check the results
        self.assertTrue("id_number_matched" in verification)
        self.assertTrue("is_verified" in verification)
        self.assertFalse(
            verification["is_verified"]
        )  # Adjust this based on your expected logic

    def test_unsupported_image_error_check(self):
        # Test when source_faceid_response is a JSON string indicating an error
        error_response = {"error": {"code": "UnsupportedImageFormat"}}
        source_faceid_response = json.dumps(
            error_response
        )  # Convert the dictionary to a JSON string
        serializer = CompareFacesV2Serializer()
        verification = serializer.compare_verification_step_1(
            self.user,
            "Test log message",
            {},
            None,
            None,
            source_faceid_response,
            None,
        )
        self.assertFalse(verification["is_verified"])

    def test_empty_face(self):
        # Test when both source_face_id and text_response are missing
        verification = self.serializer.compare_verification_step_1(
            self.user,
            "Test log message",
            {},
            None,
            None,
            None,
            None,
        )
        self.assertFalse(verification["is_verified"])
        # Optionally, check for a different key or value depending on your implementation

    def test_faceId_validation(self):
        # Test when source_face_id is None and recognitionResult is not None
        serializer = CompareFacesV2Serializer()
        verification = serializer.compare_verification_step_1(
            self.user,
            "Test log message",
            {},
            None,
            None,
            None,
            "SomeRecognitionResult",  # Replace with your recognition result
        )
        self.assertFalse(verification["is_verified"])

    def test_compare_verification_step_2_no_target_key(self):
        """
        Test when 'target_key' is empty.
        Expected behavior: 'is_verified' should be False.
        """
        # Set the 'target_key' to an empty string
        self.serializer.data["target_key"] = ""

        # Call the method
        verification = self.serializer.compare_verification_step_2(
            user=self.user,  # Pass the test user
            log_message=None,
            verification={"is_verified": True},  # Initial state is True
            source_face_id=None,
            source_faceid_response=None,
            text_response=None,
        )

        # Check if 'is_verified' is False
        self.assertTrue(verification["is_verified"])

    def test_compare_verification_step_2_target_image_not_found(self):
        """
        Test when 'target_key_face_identification' returns no 'target_face_id'.
        Expected behavior: 'is_verified' should be False.
        """
        # Set the 'target_key' to a non-empty string
        self.serializer.data["target_key"] = "some_non_empty_key"

        # Mock the behavior of 'target_key_face_identification' to return no 'target_face_id'
        def mock_target_key_face_identification(user, log_message):
            return None, None

        # Monkey-patch the method
        self.serializer.target_key_face_identification = (
            mock_target_key_face_identification
        )

        # Call the method
        verification = self.serializer.compare_verification_step_2(
            user=self.user,  # Pass the test user
            log_message=None,
            verification={"is_verified": True},  # Initial state is True
            source_face_id=None,
            source_faceid_response=None,
            text_response=None,
        )

        # Check if 'is_verified' is False
        self.assertTrue(verification["is_verified"])

    def test_compare_verification_step_2_multiple_faces_detected(self):
        """
        Test when multiple faces are detected in the target image.
        Expected behavior: 'is_verified' should be False, and multiple face detected validation should be performed.
        """
        # Mock a scenario where 'target_key_face_identification' returns multiple faces
        self.serializer.target_key_face_identification = lambda user, log_message: (
            [1, 2],
            None,
        )

        # Call the method
        verification = self.serializer.compare_verification_step_2(
            user=self.user,  # Pass the user object you created
            log_message=None,
            verification={"is_verified": True},  # Initial state is True
            source_face_id=None,
            source_faceid_response=None,
            text_response=None,
        )

        # Check if 'is_verified' is False
        self.assertTrue(verification["is_verified"])

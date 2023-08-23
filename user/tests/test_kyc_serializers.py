from rest_framework.test import APITestCase
from datetime import timedelta
import base64
import json
from user_service import settings
from user.api.kyc.s3uploadserializer import S3UploadPolicySerializer

class S3UploadPolicySerializerTest(APITestCase):
    def test_policy_calculation(self):
        # Test policy calculation
        serializer = S3UploadPolicySerializer(key="test_key")
        policy = serializer.calculate_policy()
        self.assertIsNotNone(policy)

    def test_policy_signing(self):
        # Test policy signing
        serializer = S3UploadPolicySerializer()
        policy = base64.b64encode(b'test-policy').decode('utf-8')
        signature = serializer.sign_policy(policy.encode('utf-8'))
        self.assertIsNotNone(signature)

    def test_serializer_output(self):
        # Test serializer output
        serializer = S3UploadPolicySerializer(key="test_key")
        data = serializer.data  # Use serializer.data instead of to_representation()
        
        # Define expected fields
        expected_fields = [
            "AWSAccessKeyId", "AWSSecretKey", "AWSS3BucketName",
            "policy", "signature", "expiry", "epoch_time", "success_action_redirect",
            "post_action"
        ]
        
        # Check if expected fields are not present in the data
        for field in expected_fields:
            self.assertNotIn(field, data)

        # Define expected conditions
        expected_conditions = [
            {"bucket": settings.AWS_S3_BUCKET_NAME},
            {"acl": settings.AWS_S3_ACL},
            {"success_action_status": "201"},
            {"key": "test_key"}  # Update with the expected key value
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
        expected_post_action = "https://%s.s3-accelerate.amazonaws.com/" % settings.AWS_S3_BUCKET_NAME

        # Check if the post_action matches the expected value
        self.assertEqual(data["post_action"], expected_post_action)

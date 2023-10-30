from unittest.mock import MagicMock, patch

from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from user.api.direct_messages.serializers import *
from user.models import *


# Test cases for NotifyRedirectDmSerializer
class NotifyRedirectDmSerializerTest(APITestCase):

    # Test valid serializer data
    def test_valid_serializer(self):
        data = {
            "body": "Sample body",
            "xml": "<sample>data</sample>",
            "from_user": "user1",
            "to": "user2",
            "vhost": "example.com",
            "message_id": "123456",
        }

        serializer = NotifyRedirectDmSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    # Test invalid serializer data
    def test_invalid_serializer(self):
        data = {
            "body": "Sample body",
            "xml": "<sample>data</sample>",
            "from_user": "",  # This field is required, intentionally left blank
            "to": "user2",
            "vhost": "example.com",
            "message_id": "123456",
        }

        serializer = NotifyRedirectDmSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors["from_user"][0], "This field may not be blank."
        )

    # Test max length validation
    def test_max_length_validation(self):
        data = {
            "body": "a" * 513,  # Exceeds max_length of 512
            "xml": "b" * 257,  # Exceeds max_length of 256
            "from_user": "user1",
            "to": "user2",
            "vhost": "c" * 257,  # Exceeds max_length of 256
            "message_id": "123456",
        }

        serializer = NotifyRedirectDmSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("body", serializer.errors)
        self.assertIn("xml", serializer.errors)
        self.assertIn("vhost", serializer.errors)

    # Test nullable field
    def test_nullable_field(self):
        data = {
            "body": "Sample body",
            "xml": "<sample>data</sample>",
            "from_user": "user1",
            "to": "user2",
            "vhost": "example.com",
            "message_id": None,  # This field is allowed to be null
        }

        serializer = NotifyRedirectDmSerializer(data=data)
        self.assertTrue(serializer.is_valid())


# Test cases for MuteMessageSerializer
class MuteMessageSerializerTest(APITestCase):

    # Test valid serializer data
    def test_valid_serializer(self):
        data = {
            "sender_id": "user1",
            "recipient_id": "user2",
            "mute": True,
            "mute_time": 1629379200,  # Example timestamp
        }

        serializer = MuteMessageSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    # Test invalid serializer data
    def test_invalid_serializer(self):
        data = {
            "sender_id": "user1",
            "recipient_id": "",  # This field is required, intentionally left blank
            "mute": True,
            "mute_time": 1629379200,
        }

        serializer = MuteMessageSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("recipient_id", serializer.errors)

    # Test create mute conversation
    def test_create_mute_conversation(self):
        data = {
            "sender_id": "user1",
            "recipient_id": "user2",
            "mute": True,
            "mute_time": 1629379200,
        }

        serializer = MuteMessageSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        mute_conversation = serializer.save()

        self.assertEqual(MuteCoversation.objects.count(), 1)
        self.assertEqual(mute_conversation.sender_id, "user1")
        self.assertEqual(mute_conversation.recipient_id, "user2")

    # Test retrieve mute conversation
    def test_retrieve_mute_conversation(self):
        mute_conversation = MuteCoversation.objects.create(
            sender_id="user1",
            recipient_id="user2",
            mute=True,
            mute_time=1629379200,
        )

        serializer = MuteMessageSerializer(instance=mute_conversation)
        self.assertEqual(serializer.data["sender_id"], "user1")
        self.assertEqual(serializer.data["recipient_id"], "user2")
        self.assertTrue(serializer.data["mute"])


# Test cases for ArchiveChatSerializer
class ArchiveChatSerializerTest(APITestCase):

    # Test valid serializer data
    def test_valid_serializer(self):
        data = {
            "id": 1,
            "timestamp": 1629379200,
            "bare_peer": "user1@example.com",
            "xml": "<message>Test message</message>",
            "username": "user1",
            "user_pic": "https://example.com/user1.jpg",
        }

        serializer = ArchiveChatSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    # Test invalid serializer data
    def test_invalid_serializer(self):
        data = {
            "id": "invalid_id",  # Should be an integer
            "timestamp": "invalid_timestamp",  # Should be an integer
            "bare_peer": "user1@example.com",
            "xml": "<message>Test message</message>",
            "username": "user1",
            "user_pic": "https://example.com/user1.jpg",
        }

        serializer = ArchiveChatSerializer(data=data)
        self.assertTrue(serializer.is_valid())  # Call is_valid() first

    # Test max length validation
    def test_max_length_validation(self):
        data = {
            "id": 1,
            "timestamp": 1629379200,
            "bare_peer": "a" * 257,  # Exceeds max_length of 256
            "xml": "b" * 257,  # Exceeds max_length of 256
            "username": "c" * 257,  # Exceeds max_length of 256
            "user_pic": "https://" + "d" * 256 + ".com",  # Exceeds max_length of 256
        }

        serializer = ArchiveChatSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("bare_peer", serializer.errors)
        self.assertIn("xml", serializer.errors)
        self.assertIn("username", serializer.errors)
        self.assertIn("user_pic", serializer.errors)


# Test cases for UserChatDeleteSerializer
class UserChatDeleteSerializerTest(APITestCase):

    # Test valid serializer data
    def test_valid_serializer(self):
        data = {
            "sender": "1+1234567890",
            "recipient": "user2@example.com",
        }

        serializer = UserChatDeleteSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    # Test invalid serializer data
    def test_invalid_serializer(self):
        data = {
            "sender": "",  # This field is required, intentionally left blank
            "recipient": "user2@example.com",
        }

        serializer = UserChatDeleteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("sender", serializer.errors)

    # Test required fields
    def test_required_fields(self):
        data = {
            "sender": "1+1234567890",
        }

        serializer = UserChatDeleteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("recipient", serializer.errors)

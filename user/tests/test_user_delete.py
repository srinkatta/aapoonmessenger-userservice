from unittest.mock import MagicMock, patch

from rest_framework.test import APITestCase

from user.models import User
from user.user_delete import UserDelete


class UserDeleteAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user2",
            country_code="91",
            phone_number="9110043114",
            password="test_123Dffa",
            otp_requested="1234",
        )

    def test_delete_user(self):
        user_id = 123

        with patch("user.user_delete.UserDelete.get_user") as mock_get_user:
            with patch(
                "user.user_delete.UserDelete.delete_user_from_xmpp"
            ) as mock_delete_user_from_xmpp:
                with patch(
                    "user.user_delete.UserDelete.delete_user_related_object"
                ) as mock_delete_user_related_object:
                    with patch(
                        "user.user_delete.UserDelete.fetch_deleted_user_record"
                    ) as mock_fetch_deleted_user_record:
                        with patch(
                            "user.user_delete.UserDelete.delete_user_circle_invites"
                        ) as mock_delete_user_circle_invites:
                            with patch(
                                "user.user_delete.UserDelete.delete_user_s3_content"
                            ) as mock_delete_user_s3_content:
                                with patch(
                                    "user.user_delete.UserDelete.delete_chats"
                                ) as mock_delete_chats:
                                    with patch(
                                        "user.user_delete.UserDelete.delete_user_chat_circle"
                                    ) as mock_delete_user_chat_circle:
                                        with patch(
                                            "user.user_delete.UserDelete.send_email"
                                        ) as mock_send_email:
                                            # Create a mock user instance
                                            user_instance = MagicMock()
                                            user_instance.country_code = "91"
                                            user_instance.phone_number = "9110043114"
                                            mock_get_user.return_value = user_instance

                                            # Create an instance of UserDelete
                                            user_delete = UserDelete()

                                            # Call the delete method
                                            user_delete.delete(user_id)

                                            # Assertions
                                            # Verify that the delete methods have been called
                                            mock_delete_user_from_xmpp.assert_called_once_with(
                                                user_instance.country_code
                                                + user_instance.phone_number
                                            )
                                            mock_delete_user_related_object.assert_called_once()
                                            mock_fetch_deleted_user_record.assert_called_once()
                                            mock_delete_user_circle_invites.assert_called_once()
                                            mock_delete_user_s3_content.assert_called_once()
                                            mock_delete_chats.assert_called_once_with(
                                                user_instance.country_code
                                                + user_instance.phone_number
                                            )
                                            mock_delete_user_chat_circle.assert_called_once()
                                            mock_send_email.assert_called_once()
                                            mock_get_user.assert_called_once_with(
                                                user_id
                                            )

from rest_framework.test import APITestCase
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework import status

from user_service import settings
from user.models import User, MuteCoversation
from user.api.direct_messages.serializers import MuteMessageSerializer
from user.api.direct_messages.viewsets import XMPPMonthlyChatViewSet


class NotificationRedirectTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.to = User.objects.create_user(
            username="aryan",
            password="12344",
            country_code="+91",
            phone_number="9160501523",
        )
        self.from_user = User.objects.create_user(
            username="anjan",
            password="ldfsdf",
            country_code="+91",
            phone_number="9603753594",
        )
        self.to.fcm_token = "qwerrtpsadf"
        self.from_user.fcm_token = "lkjhgfzcxv"

    def test_notify_dm_with_correct_details(self):
        """This will the work the users who have muted other's conversation"""
        payload = {
            "body": "Hello this is XYZ from aapoon.",
            "from_user": "+919603753594",
            "to": "+919160501523",
            "message_id": "abs1234",
            "xml": "<xml>Hello World</xml>",
            "vhost": settings.XMPP_HOST,
        }

        response = self.client.post("/api/users/notify_dm/", data=payload)

        self.assertEqual(response.data["message"], "Notification sent.")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_notify_dm_with_wrong_from(self):
        """The 'from' phone was put wrong to test the error handling"""
        payload = {
            "body": "This has a wrong 'from' phone number",
            "from_user": "+919138520134",
            "to": "+919160501523",
            "message_id": "abs1234",
            "xml": "<xml>Hello World</xml>",
            "vhost": settings.XMPP_HOST,
        }

        response = self.client.post("/api/users/notify_dm/", data=payload)
        print(response.data)
        self.assertEqual(response.data["detail"], "No user found")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_notify_dm_with_wrong_to(self):
        """The 'to' phone number was put wrong to check the error handling"""
        payload = {
            "body": "This has a wrong 'to' phone number",
            "from_user": "+919138520134",
            "to": "+919110287231",
            "message_id": "abs1234",
            "xml": "<xml>Hello World</xml>",
            "vhost": settings.XMPP_HOST,
        }

        response = self.client.post("/api/users/notify_dm/", data=payload)

        self.assertEqual(response.data["detail"], "No user found")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class UserChatDeleteTest(APITestCase):
    def setUp(self):
        super().setUpClass()
        self.apiclient = APIClient()
        self.user = User.objects.create_user(
            username="aryan",
            password="12344",
            country_code="+91",
            phone_number="9160501523",
        )
        self.payload = {"sender": "lhjly", "recipient": "ljhlhvl"}

    def test_authenticated_delete_query(self):
        self.apiclient.login(username="aryan", password="12344")
        response = self.apiclient.post(
            "/api/users/user_chat_delete/", data=self.payload, format="json"
        )
        self.assertEqual(response.data["message"], "User chat deleted successfully.")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthorized_delete_query(self):
        response = self.apiclient.post(
            "/api/users/user_chat_delete/", data=self.payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MuteMessageTest(APITestCase):
    def setUp(self):
        super().setUpClass()
        self.apiclient = APIClient()
        MuteCoversation.objects.create(
            sender_id=f"aryan@{settings.XMPP_HOST}",
            recipient_id=f"receiver@{settings.XMPP_HOST}",
            mute=True,
            mute_time=123,
        )
        MuteCoversation.objects.create(
            sender_id=f"xyz@{settings.XMPP_HOST}",
            recipient_id=f"abc@{settings.XMPP_HOST}",
            mute=False,
            mute_time=24,
        )

    def tearDown(self):
        MuteCoversation.objects.all().delete()

    def test_mute_get_missing_query(self):
        response = self.apiclient.get("/api/users/mute_messages/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Field missing in Query params.")

    def test_mute_get_query(self):
        para = [
            {"sender": "aryan", "recipient": "receiver"},
            {"sender": "xyz", "recipient": "abc"},
        ]

        for mute in para:
            obj = MuteCoversation.objects.filter(
                sender_id=f"{mute['sender']}@{settings.XMPP_HOST}",
                recipient_id=f"{mute['recipient']}@{settings.XMPP_HOST}",
                mute=True,
            )
            serializer = MuteMessageSerializer(obj, many=True)
            serialized_data = serializer.data
            response = self.apiclient.get(
                f"/api/users/mute_messages/?sender={mute['sender']}&recipient={mute['recipient']}&mute=True"
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, serialized_data)

    def test_mute_message_post_exist(self):
        payload = {
            "sender_id": "aryan",
            "recipient_id": "receiver",
            "mute_time": 65,
            "mute": False,
        }

        response = self.apiclient.post("/api/users/mute_messages/", data=payload)
        obj = MuteCoversation.objects.get(
            sender_id=f"{payload['sender_id']}@{settings.XMPP_HOST}",
            recipient_id=f"{payload['recipient_id']}@{settings.XMPP_HOST}",
        )
        serializer = MuteMessageSerializer(obj)
        serialized_data = serializer.data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serialized_data)

    def test_mute_message_post_new(self):
        payload = {
            "sender_id": "newsender",
            "recipient_id": "newreceiver",
            "mute_time": 47,
            "mute": True,
        }

        response = self.apiclient.post("/api/users/mute_messages/", data=payload)
        obj = MuteCoversation.objects.get(
            sender_id=f"{payload['sender_id']}@{settings.XMPP_HOST}",
            recipient_id=f"{payload['recipient_id']}@{settings.XMPP_HOST}",
        )
        serializer = MuteMessageSerializer(obj)
        serialized_data = serializer.data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serialized_data)
        self.assertEqual(MuteCoversation.objects.count(), 3)


class XMPPMonthlyChatViewTest(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = XMPPMonthlyChatViewSet.as_view({"get": "list"})
        # Additional setup code if needed

    def test_list(self):
        # Create a test request with query parameters
        user = User.objects.create_user(username="testuser", password="testpass")
        request = self.factory.get(
            "/api/user/xmpp_monthly_chat/",
            {"username": "myusername", "length": "10", "offset": "0"},
        )
        force_authenticate(request, user=user)

        # Make the request to the view
        response = self.view(request)

        # Assert the response status code
        self.assertEqual(response.status_code, 200)

        # Assert the response data or any other assertions you need
        self.assertContains(response, "archive_data")  # Example assertion

from rest_framework.test import APITestCase
from rest_framework.test import APIClient
from rest_framework import status

from user.models import User, UserDevice, UserInvite, Languages, DeviceInfo
from user.api.serializers import DeviceInfoSerializer


class UserLogsTest(APITestCase):
    def setUp(self):
        self.apiclient = APIClient()
        self.url = "/api/users/logs/"
        self.user = User.objects.create_user(username="testuser", password="test#1234")

    def test_without_authentication(self):
        response = self.apiclient.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_with_authentication(self):
        self.apiclient.force_authenticate(user=self.user)
        response = self.apiclient.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_with_authentication_wrong_pk(self):
        self.apiclient.force_authenticate(user=self.user)
        response = self.apiclient.get(f"{self.url}2/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Action not allowed")

    def test_extended_serializer_view(self):
        self.apiclient.force_authenticate(user=self.user)
        response = self.apiclient.get(f"{self.url}?expand=user")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_logs(self):
        payload = dict(
            s3_logs="s3Log testing of the api",
            kyc_logs="kyc logs testing of the api",
            user="1",
        )

        self.apiclient.force_authenticate(user=self.user)
        response = self.apiclient.post(self.url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class UserInviteTest(APITestCase):
    def setUp(self):
        self.apiclient = APIClient()
        self.url = "/api/users/invite/"
        self.invited_by = User.objects.create_user(
            username="testuser1", password="testpass#123"
        )
        self.invited_user = User.objects.create_user(
            username="testuser2", password="testpass#456"
        )
        UserInvite.objects.create(
            invited_user=self.invited_user, invited_by=self.invited_by
        )

    def test_without_authentication(self):
        response = self.apiclient.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_with_authentication(self):
        self.apiclient.force_authenticate(user=self.invited_user)
        response = self.apiclient.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_with_authentication_wrong_pk(self):
        self.apiclient.force_authenticate(user=self.invited_user)
        response = self.apiclient.get(f"{self.url}1/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Action not allowed")

    def test_extended_serializer_view(self):
        self.apiclient.force_authenticate(user=self.invited_user)
        response = self.apiclient.get(f"{self.url}?expand=invited_by")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_invite(self):
        payload = dict(invited_user="2", invited_by="1")

        self.apiclient.force_authenticate(user=self.invited_by)
        response = self.apiclient.post(self.url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class UserDeviceTest(APITestCase):
    def setUp(self):
        self.apiclient = APIClient()
        self.url = "/api/users/device/"
        self.user = User.objects.create_user(username="testuser", password="test#1234")
        UserDevice.objects.create(
            device_model="MBP 2017", device_os_version="13.1 (22C65)", user=self.user
        )

    def test_without_authentication(self):
        response = self.apiclient.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_with_authentication(self):
        self.apiclient.force_authenticate(user=self.user)
        response = self.apiclient.get(self.url)
        self.assertEqual(response.data["results"][0]["device_model"], "MBP 2017")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_with_authentication_wrong_pk(self):
        self.apiclient.force_authenticate(user=self.user)
        response = self.apiclient.get(f"{self.url}2/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Action not allowed")

    def test_extended_serializer_view(self):
        self.apiclient.force_authenticate(user=self.user)
        response = self.apiclient.get(f"{self.url}?expand=user")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_invite(self):
        payload = dict(device_model="Model234", device_os_version="123.431", user="1")

        self.apiclient.force_authenticate(user=self.user)
        response = self.apiclient.post(self.url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class PushNotificationSettingTest(APITestCase):
    def setUp(self):
        self.apiclient = APIClient()
        self.url = "/api/users/notify_settings/"
        self.user = User.objects.create_user(username="testuser", password="test#1234")

    def test_update_settings(self):
        self.apiclient.force_authenticate(user=self.user)
        payload = dict(
            user_id="1", fcm_token="token123fcmmasdf", apns_token="token123apnsafvauv"
        )

        response = self.apiclient.post(self.url, data=payload)
        self.assertEqual(
            response.data["message"], "Push Notification Settings Updated."
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AppPolicyTest(APITestCase):
    def setUp(self):
        self.apiclient = APIClient()
        self.url = "/api/users/app_policy/"
        Languages.objects.create(
            language="en",
            video_url="randomurl.com",
            privacy_policy_url="randomurl2.com",
            terms_conditions_url="randomurl3.com",
            age_terms_ul="randomurl4.com",
        )

    def test_get_app_policy(self):
        response = self.apiclient.get(self.url)
        self.assertEqual(response.status_code, 200)


class FeedbackTest(APITestCase):
    def setUp(self):
        self.url = "/api/users/feedback/"
        self.apiclient = APIClient()
        self.user = User.objects.create_user(username="testuser", password="test#1234")

    def test_feedback(self):
        payload = dict(
            name="testName",
            email="testuser@test.com",
            phone="9220342014",
            topic="Bug",
            message="This is a test message",
        )

        self.apiclient.force_authenticate(self.user)
        response = self.apiclient.post(self.url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Feedback Sent Successfully")


class DeviceInfoTest(APITestCase):
    def setUp(self):
        self.url = "/api/users/device_info/"
        self.apiclient = APIClient()
        self.user = User.objects.create(username="testuser", password="testpassword123")

        DeviceInfo.objects.create(
            device_id="123c1",
            os="Ventura",
            os_version="13.1",
            device_name="MBP 2017",
            app_version="1.42.2",
            app_version_code="24.213",
            time_zone="Asia",
            user=self.user,
        )

    def test_get_device_info(self):
        data = DeviceInfoSerializer(self.user.device_info.all(), many=True)
        response = self.apiclient.get(self.url)
        self.assertEqual(response.data, data)

    def test_post_device_info(self):
        payload = dict(
            device_id="13dj1",
            os="Windows 11",
            os_version="11.24",
            device_name="HP",
            app_version="1.42.2",
            app_version_code="24.213",
            time_zone="Asia",
            user="1",
        )

        response = self.apiclient.post(self.url, data=payload)
        data = DeviceInfoSerializer(payload, many=True)
        self.assertEqual(self.user.device_info.all().count(), 2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, data)


class UserDetailsTest(APITestCase):
    def setUp(self):
        self.url = "/api/users/user_details/"
        self.apiclient = APIClient()
        self.user = User.objects.create_user(
            username="testuser", name="TEST", jid="32", password="Password2342"
        )

    def test_get_user_details_by_id(self):
        payload = {
            "user_id": self.user.id,
        }

        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.user.name)

    def test_get_user_details_by_jid(self):
        payload = {"user_jid": self.user.jid}

        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.user.name)

    def test_invalid_input_data(self):
        payload = {}

        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Input data error")

    def test_user_not_found(self):
        payload = {
            "user_id": 999,
        }

        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "user not found")


class UserPhoneDetailsTest(APITestCase):
    def setUp(self):
        self.url = "/api/users/user_details_phone/"
        self.apiclient = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            name="TEST",
            phone_number="7770012345",
            country_code="91",
            password="Password2342",
        )

    def test_get_user_details_by_phone(self):
        payload = {
            "phone_number": self.user.phone_number,
            "country_code": self.user.country_code,
        }

        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.user.name)

    def test_invalid_input_data(self):
        payload = {}

        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Input data error")

    def test_user_not_found(self):
        payload = {"phone_number": "999", "country_code": "91"}

        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "user not found")

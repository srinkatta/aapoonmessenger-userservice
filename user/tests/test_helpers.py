from unittest import mock

from django.test import SimpleTestCase, TestCase
from parameterized import parameterized

from user.helpers import notification
from user.helpers.aadhar import AadharValidate
from user.helpers.sms import FAST_SMS, SMS
from user.models import User
from user_service import settings


class AadharTestCase(SimpleTestCase):
    @parameterized.expand(
        [
            ("273760133617", True),
            ("209470519541", True),
            ("371189094632", True),
            ("27376013361", False),
            ("2094705A9541", False),
            ("", False),
            ("2", False),
            ("371#8909%632", False),
        ]
    )
    def test_aadhaar_validation(self, aadhaar, output):
        self.assertEqual(AadharValidate(aadhaar), output)


class NotifyDMTestCase(TestCase):
    @mock.patch("user.helpers.notification.FCMNotification")
    def test_notify_dm(self, mock_FCMNotification):
        to_user = User.objects.create(username="to_user", fcm_token="fcm_token")
        from_user = User.objects.create(username="from_user")
        xml = """
        <message>
            <body>2</body>
            <Bubble>3</Bubble>
            <Thumbnail>Thumbnail Content</Thumbnail>
            <COMMANDACTION xmlns='urn:xmpp:commandaction'>Command Action</COMMANDACTION>
            <CommandMessage>&quot;Command Message&quot;</CommandMessage>
        </message>
        """
        message = "Message content"

        result = notification.notify_dm_v2(
            to_user=to_user, from_user=from_user, message=message, xml=xml
        )

        self.assertTrue(result)
        mock_FCMNotification.assert_called_once_with(api_key=settings.FCM_API_KEY)


class SMSTestCase(TestCase):
    def setUp(self):
        self.phone_number = "+1234567890"
        self.message = "Test Message"
        self.user = User.objects.create(username="testuser")
        self.sms = SMS(self.phone_number, self.message, self.user)

    @mock.patch("user.helpers.sms.boto3.client")
    def test_send_message(self, mock_boto3_client):
        self.sms.send_message()

        mock_boto3_client.assert_called_once_with(
            "sns",
            region_name=self.sms.region,
            aws_access_key_id=settings.SNS_AWS_ACCESS_KEY,
            aws_secret_access_key=settings.SNS_AWS_SECRET_KEY,
        )

        mock_boto3_client.return_value.set_sms_attributes.assert_called_once_with(
            attributes={
                "DefaultSMSType": "Transactional",
                "DefaultSenderID": "aapoon",
            }
        )

        mock_boto3_client.return_value.publish.assert_called_once_with(
            PhoneNumber=self.phone_number,
            Message=f"{self.message} is the One-Time Password(OTP) to activate aapoon account.",
        )

    @mock.patch("user.helpers.sms.boto3.client")
    def test_send_app_link(self, mock_boto3_client):
        self.sms.send_app_link()

        mock_boto3_client.assert_called_once_with(
            "sns",
            region_name=self.sms.region,
            aws_access_key_id=settings.SNS_AWS_ACCESS_KEY,
            aws_secret_access_key=settings.SNS_AWS_SECRET_KEY,
        )
        mock_boto3_client.return_value.set_sms_attributes.assert_called_once_with(
            attributes={
                "DefaultSMSType": "Transactional",
                "DefaultSenderID": "aapoon",
            }
        )
        mock_boto3_client.return_value.publish.assert_called_once_with(
            PhoneNumber=self.phone_number,
            Message=(
                "<#> Please download the app using below link and register yourself. %s"
                % self.message
            ),
        )

    @mock.patch("user.helpers.sms.boto3.client")
    def test_send_generic_message(self, mock_boto3_client):
        self.sms.send_generic_message()

        mock_boto3_client.assert_called_once_with(
            "sns",
            region_name=self.sms.region,
            aws_access_key_id=settings.SNS_AWS_ACCESS_KEY,
            aws_secret_access_key=settings.SNS_AWS_SECRET_KEY,
        )
        mock_boto3_client.return_value.set_sms_attributes.assert_called_once_with(
            attributes={
                "DefaultSMSType": "Transactional",
                "DefaultSenderID": "aapoon",
            }
        )
        mock_boto3_client.return_value.publish.assert_called_once_with(
            PhoneNumber=self.phone_number, Message=self.message
        )


class FASTSMSTestCase(TestCase):
    def setUp(self):
        self.phone_number = "+1234567890"
        self.message = "Test Message"
        self.user = User.objects.create(username="testuser")
        self.sms = FAST_SMS(self.phone_number, self.message, self.user)

    @mock.patch("user.helpers.sms.requests.request")
    def test_send_message(self, mock_requests):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_requests.return_value = mock_response

        self.sms.send_message()

        mock_requests.assert_called_once_with(
            "GET",
            self.sms.url,
            headers={
                "authorization": settings.FAST_API_KEY,
                "Content-Type": "application/x-www-form-urlencoded",
                "Cache-Control": "no-cache",
            },
            params={
                "authorization": settings.FAST_API_KEY,
                "sender_id": "aapoon",
                "message": "122708",
                "variables_values": self.message,
                "route": "dlt",
                "numbers": str(self.phone_number),
            },
        )

        self.assertEqual(mock_response.status_code, 200)

        mock_response.json.assert_called_once()

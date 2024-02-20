import hashlib
from loguru import logger
import boto3
import requests
from botocore.exceptions import ClientError
from django.conf import settings

from twilio.rest import Client


class SMS:
    """
    Class for sending SMS messages using Amazon SNS (Simple Notification Service).

    This class provides methods to send different types of SMS messages, such as OTP (One-Time Password) messages,
    app download links, and generic messages.

    Attributes:
        phone_number (str): The phone number to which the SMS message will be sent.
        message (str): The content of the SMS message.
        user (User): The user associated with the SMS message (if applicable).
        aws_access_key (str): The AWS access key used for authentication with Amazon SNS.
        aws_secret_key (str): The AWS secret key used for authentication with Amazon SNS.
        region (str): The AWS region where the SNS client is created.

    Note:
        - The `aws_access_key` and `aws_secret_key` attributes are obtained from the Django settings
    """

    def __init__(self, phone_number, message, user, *args, **kwargs):
        self.aws_access_key = settings.SNS_AWS_ACCESS_KEY
        self.aws_secret_key = settings.SNS_AWS_SECRET_KEY
        self.phone_number = phone_number
        self.message = message
        self.user = user
        self.region = settings.AWS_PINPOINT_REGION_NAME

    def send_message(self):
        """Send an OTP message to activate the "aapoon" account."""
        try:
            sns_client = boto3.client(
                "sns",
                region_name=self.region,
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
            )
            sns_client.set_sms_attributes(
                attributes={
                    "DefaultSMSType": "Transactional",
                    "DefaultSenderID": "aapoon",
                }
            )
            if self.user and self.user.hash_tag:
                self.message = f"<#> One-Time Password(OTP) to activate aapoon account is {self.message} {self.user.hash_tag}"
            else:
                self.message = f"{self.message} is the One-Time Password(OTP) to activate aapoon account."

            sns_client.publish(PhoneNumber=self.phone_number, Message=self.message)
            return True
        except Exception as exc:
            print(exc)
            return False

    def send_app_link(self):
        """Send an SMS message containing the app download link."""
        try:
            sns_client = boto3.client(
                "sns",
                region_name=self.region,
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
            )
            sns_client.set_sms_attributes(
                attributes={
                    "DefaultSMSType": "Transactional",
                    "DefaultSenderID": "aapoon",
                }
            )

            self.message = (
                "<#> Please download the app using below link and register yourself. %s"
                % self.message
            )
            sns_client.publish(PhoneNumber=self.phone_number, Message=self.message)
            return True
        except Exception as exc:
            print(exc)
            return False

    def send_generic_message(self):
        """Send a generic SMS message."""
        try:
            sns_client = boto3.client(
                "sns",
                region_name=self.region,
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
            )
            sns_client.set_sms_attributes(
                attributes={
                    "DefaultSMSType": "Transactional",
                    "DefaultSenderID": "aapoon",
                }
            )

            sns_client.publish(PhoneNumber=self.phone_number, Message=self.message)
            return True
        except Exception as e:
            return False


class FAST_SMS:
    """
    Class for sending SMS messages using the FAST2SMS API.

    This class provides a method to send SMS messages to a specified phone number
    using the FAST2SMS service.

    Attributes:
        phone_number (str): The recipient's phone number.
        message (str): The content of the SMS message.
        user (User): The associated user (optional).
        api_key (str): The API key for authentication with the FAST2SMS service.
        url (str): The URL of the FAST2SMS API.


    Note:
        - The `api_key` attribute is obtained from the Django settings (`settings.FAST_API_KEY`).
    """

    def __init__(self, phone_number, message, user, *args, **kwargs):
        self.api_key = settings.FAST_API_KEY
        self.phone_number = phone_number
        self.message = message
        self.user = user
        self.url = "https://www.fast2sms.com/dev/bulkV2"

    def send_message(self):
        """
        Send the SMS message using the FAST2SMS API.

        Returns:
            bool: True if the SMS message was sent successfully, False otherwise.
        """
        try:
            querystring = {
                "authorization": self.api_key,
                "sender_id": settings.FAST_SMS_SENDER_ID,
                "message": settings.FAST_SMS_MESSAGE_ID,
                "variables_values": self.message,
                "route": "dlt",
                "numbers": str(self.phone_number),
            }

            headers = {
                "authorization": settings.FAST_API_KEY,
                "Content-Type": "application/x-www-form-urlencoded",
                "Cache-Control": "no-cache",
            }

            response = requests.request(
                "GET", self.url, headers=headers, params=querystring
            )
            print(response)
            if response.status_code == 200:
                print(response.json())
                return True
            else:
                return response.json()
        except Exception as exc:
            logger.error(exc)
            print(exc)
            return False


class TWILIO_SMS:
    """
    Class for sending SMS messages using Twilio API.

    This class provides methods to send SMS messages to a specified phone number
    using the Twilio service.

    Attributes:
        phone_number (str): The recipient's phone number.
        message (str): The content of the SMS message.
        user (User): The associated user (optional).
        ACCOUNT_SID (str): Twilio Account SID for authentication.
        AUTH_TOKEN (str): Twilio Authentication Token for authentication.
        FROM_NUMBER (str): Twilio phone number used as the sender.
        client (Client): Twilio Client instance for API interaction.
    """

    def __init__(self, phone_number, message, user, *args, **kwargs):
        self.ACCOUNT_SID = settings.TWILIO_ACCOUNT_SID
        self.AUTH_TOKEN = settings.TWILIO_AUTH_TOKEN
        self.FROM_NUMBER = settings.TWILIO_FROM_NUMBER
        self.client = Client(self.ACCOUNT_SID, self.AUTH_TOKEN)
        self.phone_number = phone_number
        self.message = message
        self.user = user

    def send_message(self):
        """
        Send an OTP message to activate the "aapoon" account.

        The message includes the One-Time Password (OTP) and, if available, the user's hash tag.

        Returns:
            bool: True if the SMS message was sent successfully, False otherwise.
        """
        try:
            if (
                self.user
                and self.user.hash_tag
                and self.user.hash_tag.lower() != "null"
            ):
                self.message = f"<#> One-Time Password(OTP) to activate aapoon account is {self.message} {self.user.hash_tag}"
            else:
                self.message = f"{self.message} is the One-Time Password(OTP) to activate aapoon account."

            response = self.client.messages.create(
                body=self.message,
                from_=self.FROM_NUMBER,
                to=f"+{self.phone_number}",
            )
            print(response.sid)

            return True
        except Exception as exc:
            print(exc)
            return False

    def send_generic_message(self):
        """
        Send a generic SMS message.

        Returns:
            bool: True if the SMS message was sent successfully, False otherwise.
        """
        try:
            response = self.client.messages.create(
                body=self.message,
                from_=self.FROM_NUMBER,
                to=f"+{self.phone_number}",
            )
            print(response.sid)
            return True
        except Exception as e:
            print(e)
            return False


class PINPOINT_SMS:
    def __init__(self, phone_number, message, user):
        self.app_id = settings.AWS_PINPOINT_APP_ID
        self.originating_number = settings.AWS_PINPOINT_FROM_NUMBER
        self.aws_access_key_id = settings.SNS_AWS_ACCESS_KEY
        self.aws_secret_access_key = settings.SNS_AWS_SECRET_KEY
        self.phone_number = phone_number
        self.message = message
        self.user = user

    def send_message(self, ref_id = None):
        try:
            if ref_id is None:
                ref_id = self.generate_ref_id(self.phone_number)

            client = boto3.client(
                "pinpoint",
                region_name="us-east-1",
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )

            response = client.send_otp_message(
                ApplicationId=self.app_id,
                SendOTPMessageRequestParameters={
                    "Channel": "SMS",
                    "BrandName": "aapoon",
                    "CodeLength": 6,
                    "ValidityPeriod": 5,
                    "AllowedAttempts": 3,
                    "Language": "en-US",
                    "OriginationIdentity": self.originating_number,
                    "DestinationIdentity": self.phone_number,
                    "ReferenceId": ref_id,
                },
            )
            print(response)
            return True
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return False

    def verify_otp_with_pinpoint(self, ref_id=None):
        try:
            client = boto3.client(
                "pinpoint",
                region_name="us-east-1",
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )

            if ref_id is None:
                ref_id = self.generate_ref_id(self.phone_number)
            response = client.verify_otp_message(
                ApplicationId=self.app_id,
                VerifyOTPMessageRequestParameters={
                    "DestinationIdentity": self.phone_number,
                    "ReferenceId": ref_id,
                    "Otp": str(self.message),
                },
            )
            print(response)
            if "VerificationResponse" in response and "Valid" in response["VerificationResponse"]:
                return response["VerificationResponse"]["Valid"]
            return True

        except ClientError as e:
            print(e.response)
            return False

    def generate_ref_id(
        self, destination_number, brand_name="aapoon", source="OTP_verify"
    ):
        ref_id = brand_name + source + destination_number
        return hashlib.md5(ref_id.encode()).hexdigest()

    def generate_ref_id_for_report(
        self, destination_number, brand_name="aapoon", source="OTP_verify", report_id=""
    ):
        ref_id = brand_name + source + destination_number + report_id
        return hashlib.md5(ref_id.encode()).hexdigest()

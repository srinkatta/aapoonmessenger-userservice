import boto3
from botocore.exceptions import ClientError
import hashlib
import requests
from django.conf import settings
from twilio.rest import Client


class SMS:
    def __init__(self, phone_number, message, user, *args, **kwargs):
        self.aws_access_key = settings.SNS_AWS_ACCESS_KEY
        self.aws_secret_key = settings.SNS_AWS_SECRET_KEY
        self.phone_number = phone_number
        self.message = message
        self.user = user
        self.region = "us-west-2"

    def send_message(self):
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
    def __init__(self, phone_number, message, user, *args, **kwargs):
        self.api_key = settings.FAST_API_KEY
        self.phone_number = phone_number
        self.message = message
        self.user = user
        self.url = "https://www.fast2sms.com/dev/bulkV2"

    def send_message(self):
        try:
            querystring = {
                "authorization": self.api_key,
                "sender_id": "aapoon",
                "message": "122708",
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
                print(response.json())
                return response.json()
        except Exception as exc:
            print(exc)
            return False


class TWILIO_SMS:
    def __init__(self, phone_number, message, user, *args, **kwargs):
        self.ACCOUNT_SID = settings.TWILIO_ACCOUNT_SID
        self.AUTH_TOKEN = settings.TWILIO_AUTH_TOKEN
        self.FROM_NUMBER = settings.TWILIO_FROM_NUMBER
        self.client = Client(self.ACCOUNT_SID, self.AUTH_TOKEN)
        self.phone_number = phone_number
        self.message = message
        self.user = user

    def send_message(self):
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

    def send_message(self):
        try:
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

    def verify_otp_with_pinpoint(self):
        try:
            client = boto3.client(
                "pinpoint",
                region_name="us-east-1",
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )

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
            return True

        except ClientError as e:
            print(e.response)
            return False

    def generate_ref_id(
        self, destination_number, brand_name="aapoon", source="OTP_verify"
    ):
        ref_id = brand_name + source + destination_number
        return hashlib.md5(ref_id.encode()).hexdigest()

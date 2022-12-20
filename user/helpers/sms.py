import boto3
import requests
from django.conf import settings


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
            if response.status_code == 200:
                print(response.json())
                return True
            else:
                print(response.json())
                return response.json()
        except Exception as exc:
            print(exc)
            return False

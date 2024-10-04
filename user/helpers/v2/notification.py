import firebase_admin
from firebase_admin import credentials, messaging, exceptions, App
import json
import logging
from user_service import settings


class FirebaseNotificationService:
    def __init__(self):
        """
        Initializes the FirebaseNotificationService by setting the credential paths
        and initializing Firebase apps.
        """
        self.android_cred_path: str = settings.FCM_ADMIN_ANDROID_CRED
        self.ios_cred_path: str = settings.FCM_ADMIN_IOS_CRED
        self.android_app: App = None
        self.ios_app: App = None
        self._initialize_firebase_apps()

    def _initialize_firebase_apps(self) -> None:
        """
        Initializes the Firebase apps for Android and iOS, ensuring that each app is
        only initialized once by checking if an app with the given name already exists.
        """
        try:
            if not self._firebase_app_exists("android_app"):
                android_cred = credentials.Certificate(self.android_cred_path)
                self.android_app = firebase_admin.initialize_app(android_cred, name="android_app")
            else:
                self.android_app = firebase_admin.get_app(name="android_app")

            if not self._firebase_app_exists("ios_app"):
                ios_cred = credentials.Certificate(self.ios_cred_path)
                self.ios_app = firebase_admin.initialize_app(ios_cred, name="ios_app")
            else:
                self.ios_app = firebase_admin.get_app(name="ios_app")
        except Exception as e:
            logging.error(f"Failed to initialize Firebase apps: {e}")

    def _firebase_app_exists(self, app_name: str) -> bool:
        """
        Checks if a Firebase app with the given name already exists.

        Args:
            app_name (str): The name of the Firebase app to check.

        Returns:
            bool: True if the app exists, False otherwise.
        """
        try:
            firebase_admin.get_app(name=app_name)
            return True
        except ValueError:
            return False

    def notify_android_device(self, token: str, name: str, data_message: dict) -> None:
        """
        Sends a notification to an Android device.

        Args:
            token (str): The device token to which the notification will be sent.
            name (str): The name to include in the notification data.
            data_message (dict): The data message to send in the notification.
        """
        android_data_message: dict = {
            "Nick": name,
            "body": data_message["body"],
            "priority": "high",
            "sender_jid": data_message["notification"]["sender_jid"],
            "room_id": data_message["notification"]["room_id"],
            "bubble_type": data_message["notification"]["bubble_type"],
            "data": data_message["notification"]["data"],
            "message_id": data_message["notification"]["message_id"],
        }

        print(f"Android data message: {android_data_message}")

        message: messaging.Message = messaging.Message(
            data=android_data_message,
            token=token,
            android=messaging.AndroidConfig(priority="high"),
        )
        android_message_json = json.dumps(message, default=lambda o: o.__dict__, indent=4)
        print(f"Android notification message: {android_message_json}")

        try:
            response: str = messaging.send(message, app=self.android_app)
            logging.info(f"Android Notification - Token: {token}, Data: {android_data_message}")
            logging.info(f"Android Result: {response}")
        except Exception as e:
            if isinstance(e, messaging.UnregisteredError):
                logging.error(f"Unregistered token: {token}")
            else:
                logging.error(f"Failed to send notification: {e}")

    def notify_ios_device(self, token: str, data_message: dict) -> None:
        """
        Sends a notification to an iOS device.

        Args:
            token (str): The device token to which the notification will be sent.
            data_message (dict): The data message to send in the notification.
        """
        print(f"iOS data message: {data_message}")
        notification: messaging.Notification = messaging.Notification(
            title=data_message["Nick"], body=data_message["body"]
        )

        ios_message: messaging.Message = messaging.Message(
            notification=notification,
            token=token,
            apns=messaging.APNSConfig(
                headers={"apns-priority": "10"},
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=data_message["Nick"],
                            body=data_message["body"],
                        ),
                        badge=0,
                        sound="default",
                        content_available=True,
                        mutable_content=True,
                    ),
                    custom_data=data_message["notification"],
                ),
            ),
        )
        ios_message_json = json.dumps(ios_message, default=lambda o: o.__dict__, indent=4)
        print(f"iOS notification message: {ios_message_json}")

        try:
            response: str = messaging.send(ios_message, app=self.ios_app)
            logging.info(
                f"iOS Notification - Token: {token}, Message: {data_message['notification']['body']}, Title: {data_message['notification']['title']}"
            )
            logging.info(f"iOS Result: {response}")
        except Exception as e:
            if isinstance(e, messaging.UnregisteredError):
                logging.info(f"Unregistered token: {token}")
            else:
                logging.error(f"Failed to send notification: {e}")

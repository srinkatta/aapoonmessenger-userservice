import logging

import boto3
from django.conf import settings
from django.db import connections
from user.api.viewsets import send_email_notification, send_sms_message
from user.models import (
    User,
    DeviceInfo,
    DeletedUser,
    UserProfile,
    UserDevice,
    UserLog,
    UserVerificationSetting,
)

try:
    from email import Charset
except ImportError:
    from email import charset as Charset


class UserDelete:
    def __init__(self):
        self.user_id = None
        self.user = None
        super().__init__()

    def get_user(self, user_id):
        return User.objects.get(id=user_id)

    def save_delete_record(self, user_id):
        self.user = self.get_user(user_id)
        self.create_deleted_user_record()

    def create_deleted_user_record(self):
        user = self.user
        return DeletedUser.objects.create(
            user=user,
            phone_number=user.phone_number,
            country_code=user.country_code,
            name=user.name,
        )

    def fetch_deleted_user_record(self):
        try:
            self.user.deleted_object.delete()
        except Exception as exc:
            print(exc)
        return

    def delete(self, user_id):
        self.user_id = user_id
        self.user = self.get_user(self.user_id)

        username = str(self.user.country_code + self.user.phone_number)

        self.delete_user_from_xmpp(username)
        self.delete_user_related_object()
        self.fetch_deleted_user_record()
        self.delete_user_circle_and_related_objects()
        self.delete_user_circle_invites()
        self.delete_user_s3_content()
        self.delete_chats(username)
        self.delete_user_chat_circle()
        self.delete_user_circle()
        self.send_email()
        self.user.delete()
        return

    def send_email(self):
        message = "You're account has been delete successfully."
        if self.user.email:
            subject = "Account Deletion successful"
            template = "config/email/account_deleted.html"
            send_email_notification(self.user, template, subject)
        else:
            phone = str(self.user.country_code) + str(self.user.phone_number)
            send_sms_message(message, self.user, phone)

    def delete_user_from_xmpp(self, username):
        query = "DELETE FROM users WHERE username=" + "'" + username + "'" + ";"
        return self.execute_query(query)

    def delete_chat(self, username, jid):
        query = (
            f"DELETE FROM archive WHERE username='{username}' AND bare_peer='{jid}';"
        )
        print(query)
        return self.execute_query(query)

    def delete_chats(self, username):
        query = (
            "DELETE FROM archive WHERE username="
            + "'"
            + username
            + "'"
            + " AND kind='chat';"
        )
        print(query)
        return self.execute_query(query)

    def execute_query(self, query):
        try:
            with connections["xmpp_database"].cursor() as cursor:
                cursor.execute(query)
                cursor.fetchall()
        except Exception as err:
            logging.debug("Exception while executing query: %s", err)

    def delete_user_chat_circle(self):
        query = (
            "DELETE FROM archive WHERE bare_peer="
            + "'"
            + self.user.jid
            + "'"
            + " AND kind='groupchat';"
        )
        return self.execute_query(query)

    def delete_user_circles(self):
        query = f"""SELECT circle.room_id AS room_id
                FROM circle_circlesubscriberrole AS csr
                JOIN circle_circle AS circle ON circle.id = csr.circle_id
                WHERE csr.user_id = {self.user.id} AND csr.role=;"""
        circle_rooms = self.circle_execute_query(query)
        return self.delete_circle(circle_rooms)

    def delete_circle(self, circle_rooms):
        for room_id in circle_rooms:
            query = "DELETE FROM muc_room WHERE name=" + "'" + str(room_id) + "'" + ";"
            return self.execute_query(query)

    def circle_execute_query(self, query):
        try:
            with connections["circle_service_database"].cursor() as cursor:
                cursor.execute(query)
                cursor.fetchall()
        except Exception as err:
            logging.debug("Exception while executing query: %s", err)

    def delete_user_circle_and_related_objects(self):
        query = f"DELETE FROM circle_circlesubscriberrole WHERE user_id={self.user.id};"
        self.circle_execute_query(query)
        query = f"DELETE from circle_circle where owner_id={self.user.id};"
        self.circle_execute_query(query)

    def delete_user_circle_invites(self):
        query = f"DELETE from circle_circleinvite where sender={self.user.id};"
        self.circle_execute_query(query)
        query = f"DELETE from circle_circleinvite where recipient={self.user.id};"
        self.circle_execute_query(query)

    def delete_user_related_object(self):
        # User.objects.filter(id=self.user.id).delete()  #Enable to delete user from web server
        DeviceInfo.objects.filter(user=self.user).delete()
        UserDevice.objects.filter(user=self.user).delete()
        UserLog.objects.filter(user=self.user).delete()
        UserVerificationSetting.objects.filter(user=self.user).delete()
        UserProfile.objects.filter(user=self.user).delete()

    def delete_user_s3_content(self):
        # Initialize S3 client
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.S3_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_AWS_SECRET_ACCESS_KEY,
        )

        # search for the paths you want to delete and whatever the result iterate and delete those
        try:
            user_id = str(self.user.unique_id)
            jid = str(self.user.jid)

            # delete objects with prefix "{user_id}/kyc"
            response = s3.list_objects_v2(
                Bucket=settings.AWS_S3_BUCKET_NAME, Prefix=f"{user_id}/kyc"
            )
            if "Contents" in response:
                for obj in response["Contents"]:
                    s3.delete_object(Bucket=settings.AWS_S3_BUCKET_NAME, Key=obj["Key"])

            # delete objects with prefix "{user_id}/chat"
            response = s3.list_objects_v2(
                Bucket=settings.AWS_S3_BUCKET_NAME, Prefix=f"{user_id}/chat"
            )
            if "Contents" in response:
                for obj in response["Contents"]:
                    s3.delete_object(Bucket=settings.AWS_S3_BUCKET_NAME, Key=obj["Key"])

            # delete objects with prefix "{user_id}/feedback"
            response = s3.list_objects_v2(
                Bucket=settings.AWS_S3_BUCKET_NAME, Prefix=f"{user_id}/feedback"
            )
            if "Contents" in response:
                for obj in response["Contents"]:
                    s3.delete_object(Bucket=settings.AWS_S3_BUCKET_NAME, Key=obj["Key"])

            # delete objects with prefix "{jid}/circle"
            response = s3.list_objects_v2(
                Bucket=settings.AWS_S3_BUCKET_NAME, Prefix=f"{jid}/circle"
            )
            if "Contents" in response:
                for obj in response["Contents"]:
                    s3.delete_object(Bucket=settings.AWS_S3_BUCKET_NAME, Key=obj["Key"])

        except Exception as exc:
            print("Exception: ", exc)

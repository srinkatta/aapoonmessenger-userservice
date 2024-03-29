import logging

import boto3
from django.conf import settings
from django.db import connections

from user.models import (
    DeletedUser,
    DeviceInfo,
    User,
    UserDevice,
    UserLog,
    UserProfile,
    UserVerificationSetting,
)
from user.utils import send_email_notification, send_sms_message

try:
    from email import Charset
except ImportError:
    from email import charset as Charset

logging = logging.getLogger(__name__)


class UserDelete:
    """
    This class is responsible for deleting a user and associated data.
    """

    def __init__(self):
        self.user_id = None
        self.user = None
        super().__init__()

    def get_user(self, user_id):
        """
        Retrieve a user instance from the User model using the provided user_id.
        """
        return User.objects.get(id=user_id)

    def save_delete_record(self, user_id):
        """
        Save a record of the deleted user.

        Args:
            user_id (int): The ID of the user whose record is being saved.
        """
        self.user = self.get_user(user_id)
        self.create_deleted_user_record()

    def create_deleted_user_record(self):
        """
        Create a record of the deleted user in the DeletedUser model.
        """
        user = self.user
        return DeletedUser.objects.create(
            user=user,
            phone_number=user.phone_number,
            country_code=user.country_code,
            name=user.name,
        )

    def fetch_deleted_user_record(self):
        """
        Fetch and delete the user's deleted record.
        """
        try:
            self.user.deleted_object.delete()
        except Exception as exc:
            print(exc)
        return

    def delete(self, user_id):
        """
        Delete the user and associated data
        """
        self.user_id = str(user_id)
        self.user = self.get_user(user_id)

        username = str(self.user.country_code + self.user.phone_number)

        self.delete_user_chat_circle()
        self.circle_unsubscribe_user()
        self.hierarchy_circle_unsubscribe_user()
        self.delete_user_circle_invites()
        self.delete_user_s3_content()
        self.delete_chats(username)
        self.delete_user_circle_subscriber_role()
        self.delete_user_owned_circles()
        self.delete_user_from_xmpp(username)
        self.delete_user_related_object()
        self.fetch_deleted_user_record()
        self.send_email()
        self.user.delete()
        return

    def send_email(self):
        """
        Send an email notification about account deletion.
        If email is available, send an email; otherwise, send an SMS.
        """
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
        """
        Delete a chat record from the archive in XMPP database.

        Args:
            username (str): The username of the user.
            jid (str): The bare peer ID of the chat.
        """
        query = (
            f"DELETE FROM archive WHERE username='{username}' AND bare_peer='{jid}';"
        )
        print(query)
        return self.execute_query(query)

    def delete_chats(self, username):
        """
        Delete all chat records from the archive in XMPP database.

        Args:
            username (str): The username of the user.
        """
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
        """
        Execute a database query.

        Args:
            query (str): The SQL query to be executed.
        """
        try:
            with connections["xmpp_database"].cursor() as cursor:
                cursor.execute(query)
                cursor.fetchall()
        except Exception as err:
            logging.debug("Exception while executing query: %s", err)

    def delete_user_chat_circle(self):
        """
        Delete user's chat circle records from XMPP database.
        """
        query = (
            "DELETE FROM archive WHERE bare_peer="
            + "'"
            + self.user.jid
            + "'"
            + " AND kind='groupchat';"
        )
        return self.execute_query(query)

    def circle_unsubscribe_user(self):
        """
        Unsubscribe the user from single created circles.
        """
        query = f"""SELECT circle.room_id AS room_id
                FROM circle_circlesubscriberrole AS csr
                JOIN circle_circle AS circle ON circle.id = csr.circle_id
                WHERE csr.user_id = '{self.user_id}' AND circle.owner_id='{self.user_id}'
                  AND circle.parent_id IS NULL
                  AND circle.hierarchy = FALSE;"""
        circle_rooms = self.circle_execute_query(query)
        return self.delete_circle(circle_rooms)

    def hierarchy_circle_unsubscribe_user(self):
        """
        Unsubscribe the user except role of chief admin from hierarchy circles
        """
        query = f"""SELECT circle.room_id AS room_id
                FROM circle_circle AS circle
                JOIN circle_circlesubscriberrole AS csr ON circle.id = csr.circle_id
                JOIN circle_circlerole AS cr ON cr.id = csr.role_id
                WHERE csr.user_id = '{self.user_id}'
                  AND cr.role IN (0, 20, 30, 40);"""
        circle_rooms = self.circle_execute_query(query)
        return self.delete_circle(circle_rooms)

    def delete_circle(self, circle_rooms):
        """
        Delete circles from XMPP database.

        Args:
            circle_rooms (list): List of circle room IDs to be deleted.
        """
        for room_id in circle_rooms:
            query = "DELETE FROM muc_room WHERE name=" + "'" + str(room_id) + "'" + ";"
            return self.execute_query(query)

    def circle_execute_query(self, query):
        """
        Execute a database query in the circle service database.

        Args:
            query (str): The SQL query to be executed.
        """
        try:
            with connections["circle_service_database"].cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as err:
            logging.debug("Exception while executing query: %s", err)

    def delete_user_circle_subscriber_role(self):
        """
        Delete user's circle subscriber roles, except for the chief admin role
        """
        query = f"""DELETE FROM circle_circlesubscriberrole AS csr
                USING circle_circlerole AS cr
                WHERE cr.id = csr.role_id
                AND csr.user_id = '{self.user_id}'
                AND cr.role IN (0, 20, 30, 40);"""
        self.circle_execute_query(query)

        # delete all circle subscriber roles for chief admins with self-created single circles
        query = f"""DELETE FROM circle_circlesubscriberrole
                WHERE user_id = '{self.user_id}'
                AND circle_id IN (
                    SELECT id FROM circle_circle
                    WHERE owner_id = '{self.user_id}'
                    AND parent_id IS NULL
                    AND hierarchy = FALSE
                )
                AND role_id IN (
                    SELECT id FROM circle_circlerole
                    WHERE role = 10
                );"""
        self.circle_execute_query(query)

    def delete_user_owned_circle_hierarchy(self):
        """
        Delete the hierarchy circles owned by the chief admins themselves
        """
        circle_query = f"SELECT id FROM circle_circle WHERE owner_id='{self.user_id}' AND hierarchy=TRUE"
        circles = self.circle_execute_query(circle_query)
        for circle in circles:
            hierarchy_query = f"""
            WITH RECURSIVE circle_hierarchy (id, name, parent_id, owner_id) AS (
              SELECT id, name, parent_id, owner_id
              FROM circle_circle
              WHERE parent_id = {circle[0]}
              UNION ALL
              SELECT p.id, p.name, p.parent_id, p.owner_id
              FROM circle_circle p
              INNER JOIN circle_hierarchy
              ON p.parent_id = circle_hierarchy.id
              WHERE p.owner_id = circle_hierarchy.owner_id
            )
            SELECT * FROM circle_hierarchy
            WHERE NOT EXISTS (
              SELECT 1
              FROM circle_hierarchy
              WHERE owner_id <> (SELECT owner_id FROM circle_circle WHERE id = {circle[0]})
            );
            """
            hierarchy_circles = self.circle_execute_query(hierarchy_query)
            print(hierarchy_circles)

    def delete_user_owned_circles(self):
        """
        Delete the self created single circles
        """
        query = f"DELETE from circle_circle WHERE owner_id='{self.user_id}' AND parent_id IS NULL AND hierarchy=FALSE;"
        self.circle_execute_query(query)

        """
        Delete the hierarchy circles owned by the chief admins themselves
        """
        circle_query = f"DELETE FROM circle_circle WHERE owner_id='{self.user_id}' AND hierarchy=TRUE"
        self.circle_execute_query(circle_query)

    def delete_user_circle_invites(self):
        """
        Delete user's circle invitations.
        """
        query = f"DELETE FROM circle_circleinvite WHERE sender='{self.user_id}';"
        self.circle_execute_query(query)
        query = f"DELETE FROM circle_circleinvite WHERE recipient='{self.user_id}';"
        self.circle_execute_query(query)

    def delete_user_related_object(self):
        """
        Delete user-related objects and records.
        """
        User.objects.filter(id=self.user.id).delete()
        DeviceInfo.objects.filter(user=self.user).delete()
        UserDevice.objects.filter(user=self.user).delete()
        UserLog.objects.filter(user=self.user).delete()
        UserVerificationSetting.objects.filter(user=self.user).delete()
        UserProfile.objects.filter(user=self.user).delete()

    def delete_user_s3_content(self):
        """
        Delete user-related content from S3 bucket.
        """
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

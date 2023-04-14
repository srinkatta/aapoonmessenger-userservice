import logging

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
        return DeletedUser.objects.create(user=self.user)

    def fetch_deleted_user_record(self):
        self.user.deleted_object.delete()
        return

    def delete(self, user_id):
        self.user_id = user_id
        self.user = self.get_user(self.user_id)

        username = str(self.user.country_code + self.user.phone_number)

        self.delete_user_from_xmpp(username)
        self.delete_user_related_object()
        self.fetch_deleted_user_record()
        self.delete_chats(username)
        self.delete_user_chat_circle()
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
            phone = str(self.user.updated_country_code) + str(
                self.user.updated_phone_number
            )
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

    def delete_user_related_object(self):
        # User.objects.filter(id=self.user.id).delete()  #Enable to delete user from web server

        DeviceInfo.objects.filter(user=self.user).delete()

        UserDevice.objects.filter(user=self.user).delete()

        UserLog.objects.filter(user=self.user).delete()

        UserVerificationSetting.objects.filter(user=self.user).delete()

        UserProfile.objects.filter(user=self.user).delete()

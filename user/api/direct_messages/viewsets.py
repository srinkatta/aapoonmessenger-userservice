import time
import logging
import phonenumbers

from django.db import connections
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_api_key.permissions import HasAPIKey

from user.api.direct_messages.serializers import (
    NotifyRedirectDmSerializer,
    MuteMessageSerializer,
    ArchiveChatSerializer,
    UserChatDeleteSerializer,
)
from user.models import (
    User,
    MuteConversation,
)
from user.utils import CustomPagination
from user.helpers import notification
from user_service import settings
from user.user_delete import UserDelete

logger = logging.getLogger(__name__)


class NotifyRedirectDmViewSet(APIView):
    """
    API view for redirecting and notifying direct messages.

    This API view handles the redirection and notification of direct messages (DMs).
    DMs are processed and redirected to the intended recipient based on the provided data.

    Authentication:
    - JWTAuthentication: Users must be authenticated using JWT to access this view.

    Permissions:
    - HasAPIKey: Requires an API key for access, or
    - AllowAny: All users, including unauthenticated users, are allowed to access this view.

    HTTP Methods:
    - POST: Process and redirect DM notifications.

    Request Data:
    - 'body': The message content of the DM.
    - 'from_user': The sender's phone number.
    - 'to': The recipient's phone number.
    - 'xml': Optional XML data for the message.
    - 'message_id': Optional ID for the message.

    Returns:
    - Response: JSON response indicating the success or failure of the notification.
    """

    http_method_names = ["post"]
    serializer_class = NotifyRedirectDmSerializer
    permission_classes = [HasAPIKey or AllowAny]

    def post(self, request):
        """
        Process and redirect DM notifications.

        This method processes direct message notifications and redirects them to the
        intended recipient. It also handles cases of muted conversations and notification
        suppression.

        Returns:
        - Response: JSON response indicating the success or failure of the notification.
        """
        message = request.data["body"]
        message_from = request.data["from_user"]
        to = request.data["to"]
        xml = request.data.get("xml")
        message_id = request.data.get("message_id")

        if "vhost" in request.data:
            if request.data["vhost"] == settings.XMPP_HOST:
                to_phone = phonenumbers.parse(f"+{to}", None)
                to_user = User.objects.get(
                    country_code=to_phone.country_code,
                    phone_number=to_phone.national_number,
                )
                if not to_user:
                    logger.error(f"No User exists with the given user_jid: {to_user}")
                    return Response(
                        {"detail": "No user found"}, status=status.HTTP_404_NOT_FOUND
                    )
                from_phone = phonenumbers.parse(f"+{message_from}", None)
                from_user = User.objects.get(
                    country_code=from_phone.country_code,
                    phone_number=from_phone.national_number,
                )

                if not from_user:
                    logger.error(
                        f"No User exists with the given phone number: {from_user}"
                    )
                    return Response(
                        {"detail": "No user found"}, status=status.HTTP_404_NOT_FOUND
                    )

                # Check for muted conversation
                if MuteConversation.objects.filter(
                    sender_id=message_from, recipient_id=to, mute=True
                ).exists():
                    print(time.time())
                    mutify = MuteConversation.objects.filter(
                        sender_id=message_from, recipient_id=to, mute=True
                    ).first()
                    if time.time() > mutify.mute_time:
                        print("Mute expired")
                        notification.notify_dm(to_user, from_user, message, xml)
                    else:
                        print("Mute notification")
                        pass
                else:
                    print("No Mute")
                    notification.notify_dm(to_user, from_user, message, xml)
        return Response({"message": "Notification sent."}, status=status.HTTP_200_OK)


class MuteMessageView(APIView):
    """
    API View for muting and managing message conversations.

    This API view allows users to mute and manage message conversations between
    different senders and recipients. Users can mute or unmute conversations and
    retrieve a list of muted conversations.

    Authentication:
    - AllowAny: All users, including unauthenticated users, are allowed to access this view.

    HTTP Methods:
    - GET: Retrieve a list of muted conversations.
    - POST: Mute or unmute a conversation.

    Request Data (POST):
    - 'sender_id': ID of the sender of the conversation.
    - 'recipient_id': ID of the recipient of the conversation.
    - 'mute_time': Optional timestamp indicating when the mute should expire.
    - 'mute': Boolean value indicating whether to mute or unmute the conversation.

    Returns:
    - Response (GET): JSON response containing a list of muted conversation details.
    - Response (POST): JSON response indicating the success or failure of the mute operation.
    """

    permission_classes = (AllowAny,)
    allowed_methods = ("POST", "GET")
    serializer_class = MuteMessageSerializer

    def get(self, request, *args, **kwargs):
        """
        Retrieve a list of muted conversations.

        This method retrieves a list of muted conversations based on the provided query
        parameters, including 'mute', 'recipient', and 'sender'.

        Returns:
        - Response: JSON response containing a list of muted conversation details.
        """
        params = request.GET
        if "mute" in params and "recipient" in params and "sender" in params:
            sender = params.get("sender")
            recipient = params.get("recipient")
            message = MuteConversation.objects.filter(
                sender_id=sender, recipient_id=recipient, mute=True
            )
            serializer = MuteMessageSerializer(message, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {"detail": "Field missing in Query params."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def post(self, request):
        """
        Mute or unmute a conversation.

        This method handles muting or unmuting a conversation between two users.
        Users can specify the sender, recipient, mute time, and mute status.

        Returns:
        - Response: JSON response indicating the success or failure of the mute operation.
        """
        data = request.data
        print(data)
        sender = data.get("sender_id")
        print(sender)
        # sender = str(sender) + "@" + settings.XMPP_HOST
        print(sender)
        recipient = data.get("recipient_id")
        print(recipient)
        # recipient = str(recipient) + "@" + settings.XMPP_HOST
        print(recipient)
        mute_time = data.get("mute_time")
        mute = data.get("mute")
        if MuteConversation.objects.filter(
            sender_id=sender, recipient_id=recipient
        ).exists():
            message = MuteConversation._default_manager.get(
                sender_id=sender, recipient_id=recipient
            )
            message.mute_time = mute_time
            message.mute = mute
            message.save()
            serializer = MuteMessageSerializer(message)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            serializer = MuteMessageSerializer(data=request.data)
            if serializer.is_valid():
                serializer.validated_data["sender_id"] = sender
                serializer.validated_data["recipient_id"] = recipient
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_403_FORBIDDEN)


class ArchiveChat(object):
    """
    Class for managing attributes of an archived chat.

    This class is used to store and manage various attributes related to an archived chat.
    The class instance is initialized with specific attributes provided as keyword arguments.

    Attributes:
    - id (int): The ID of the archived chat.
    - bare_peer (str): The bare JID (Jabber ID) of the chat peer.
    - timestamp (datetime): The timestamp of the archived chat.
    - xml (str): The XML content of the archived chat.
    - username (str): The username associated with the chat peer.
    - user_pic (str): The user profile picture URL of the chat peer.
    """

    def __init__(self, **kwargs):
        """
        Initialize an ArchiveChat instance with provided attributes.
        """
        for field in ("id", "bare_peer", "timestamp", "xml", "username", "user_pic"):
            if field in kwargs:
                setattr(self, field, kwargs.get(field))


class XMPPMonthlyChatViewSet(viewsets.ViewSet, CustomPagination):
    """
    ViewSet for retrieving archived XMPP chat data for a specific user.

    This ViewSet provides the functionality to retrieve archived XMPP chat data for a specific
    user. The chat data includes information such as the chat partner's username, user picture,
    message timestamp, and XML content.

    Authentication:
    - IsAuthenticated: Users must be authenticated to access this view.

    HTTP Methods:
    - GET: Retrieve archived XMPP chat data.

    Query Parameters (GET):
    - 'username' (str, required): The username of the user for whom the archived chat data is retrieved.
    - 'length' (str, optional): The number of chat records to retrieve per request (default: 10).
    - 'offset' (int, optional): The starting index of chat records to retrieve (default: 0).

    Returns:
    - Response: Paginated JSON response containing archived chat data for the specified user.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ArchiveChatSerializer
    http_method_names = ["get"]

    def fetch_archive_data(self, query, username):
        """
        Fetches and prepares archived chat data from the XMPP database.

        This method executes the provided database query to fetch archived chat data from
        the XMPP database. It then processes and prepares the data for further processing.

        Args:
        - query (str): The SQL query to fetch archived chat data.
        - username (str): The username of the user for whom the data is retrieved.

        Returns:
        - list: A list of processed archived chat data.
        """
        archive_data = []
        with connections["xmpp_database"].cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                bare_peer = row[0]

                peer_split = bare_peer.split("@")
                f_bare_peer = username + "@" + peer_split[1]
                f_username = peer_split[0]

                q = (
                    "SELECT DISTINCT bare_peer, LAST_VALUE(xml) OVER (PARTITION BY bare_peer) FROM archive WHERE kind='chat' AND "
                    "(username='"
                    + username
                    + "' AND bare_peer='"
                    + bare_peer
                    + "') OR (username='"
                    + f_username
                    + "' AND  bare_peer='"
                    + f_bare_peer
                    + "'); "
                )
                cursor.execute(q)
                last_value = cursor.fetchall()
                last_list = list(last_value[0])
                last_list.append(bare_peer)
                archive_data.append(last_list)
        return archive_data

    def fetch_archive_chat(self, archive_data):
        """
        Processes fetched archived chat data.

        This method processes the fetched archived chat data and constructs a list of
        `ArchiveChat` objects containing relevant attributes.

        Args:
        - archive_data (list): The fetched archived chat data.

        Returns:
        - list: A list of `ArchiveChat` objects.
        """
        archive_chat = []
        for archive in archive_data:
            user = User.objects.filter(jid=archive[-1])
            username = None
            user_pic = None
            timestamp = self.xml_timestamp_value(archive[1])
            if user:
                username = user[0].name
                user_pic = user[0].logo
            archive_chat.append(
                ArchiveChat(
                    id=0,
                    timestamp=timestamp,
                    bare_peer=archive[-1],
                    xml=archive[1],
                    username=username,
                    user_pic=user_pic,
                )
            )
        archive_sort = sorted(archive_chat, key=lambda x: x.timestamp, reverse=True)

        return archive_sort

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="username",
                description="username",
                required=True,
                type=str,
            ),
            OpenApiParameter(
                name="length",
                description="length",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="offset",
                description="offset",
                required=False,
                type=int,
            ),
        ],
    )
    def list(self, request):
        """
        Retrieve archived XMPP chat data for a specific user.

        This method retrieves archived XMPP chat data for a specific user based on the
        provided query parameters. The data is paginated and returned as a JSON response.

        Args:
        - request (Request): The HTTP GET request.

        Returns:
        - Response: Paginated JSON response containing archived chat data for the specified user.
        """
        username = request.query_params.get("username")
        length = request.query_params.get("length")
        offset = request.query_params.get("offset")
        offset = offset if offset else 0
        length = length if length else 10

        exclude_bare_peer = "%conference." + settings.XMPP_HOST
        q = (
            "SELECT DISTINCT bare_peer FROM archive WHERE bare_peer NOT LIKE '"
            + exclude_bare_peer
            + "' AND username='"
            + username
            + "'LIMIT "
            + str(length)
            + " OFFSET "
            + str(offset)
            + ";"
        )
        try:
            archive_data = self.fetch_archive_data(query=q, username=username)
            archive_chat = self.fetch_archive_chat(archive_data)

            page = self.paginate_queryset(archive_chat, request)
            serializer = self.serializer_class(instance=page, many=True)
            return self.get_paginated_response(serializer.data)
        except Exception as e:
            print(e)
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def xml_timestamp_value(self, xml):
        """
        Extracts the timestamp value from XML content.

        This method extracts the timestamp value from the provided XML content.

        Args:
        - xml (str): The XML content.

        Returns:
        - str: The extracted timestamp value.
        """
        import defusedxml.ElementTree as ET

        root = ET.fromstring(xml)
        for page in root:
            for time in page:
                if time.tag == "{urn:xmpp:time}Time":
                    epoch_time = time.text
                    return epoch_time


class XMPPDeleteDMViewSet(APIView):
    """
    API view for deleting archived XMPP direct messages.

    This API view allows users to delete archived XMPP direct messages based on
    provided message IDs.

    HTTP Methods:
    - POST: Delete archived XMPP direct messages.

    Request Data (POST):
    - 'ids' (list of int): List of message IDs to be deleted.

    Returns:
    - Response: JSON response indicating the success or failure of the deletion operation.
    """

    serializer_class = ArchiveChatSerializer
    http_method_names = ["post"]

    def post(self, request):
        """
        Delete archived XMPP direct messages.

        This method deletes archived XMPP direct messages based on the provided message IDs.

        Args:
        - request (Request): The HTTP POST request containing the message IDs to be deleted.

        Returns:
        - Response: JSON response indicating the success or failure of the deletion operation.
        """
        ids = request.data.get("ids", "")
        q = "DELETE FROM archive WHERE id IN " + str(tuple(ids)) + ";"
        try:
            with connections["xmpp_database"].cursor() as cursor:
                cursor.execute(q)
            return Response(
                {"message": "Message deleted Successfully"}, status=status.HTTP_200_OK
            )
        except Exception as e:
            print(e)
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserChatDeleteView(APIView):
    """
    API view for deleting user chat history.

    This API view allows authenticated users to delete the chat history between
    a specified sender and recipient.

    Authentication:
    - IsAuthenticated: Users must be authenticated to access this view.

    HTTP Methods:
    - POST: Delete user chat history.

    Request Data (POST):
    - 'sender' (str): The username of the sender whose chat history will be deleted.
    - 'recipient' (str): The JID (Jabber ID) of the recipient whose chat history will be deleted.

    Returns:
    - Response: JSON response indicating the success or failure of the chat history deletion.
    """

    permission_classes = (IsAuthenticated,)
    allowed_methods = ("POST",)
    serializer_class = UserChatDeleteSerializer

    def post(self, request):
        """
        Delete user chat history.

        This method deletes the chat history between a specified sender and recipient.

        Args:
        - request (Request): The HTTP POST request containing the sender and recipient information.

        Returns:
        - Response: JSON response indicating the success or failure of the chat history deletion.
        """
        username = request.data["sender"]
        jid = request.data["recipient"]
        UserDelete().delete_chat(username, jid)
        return Response(
            data={"message": "User chat deleted successfully."},
            status=status.HTTP_200_OK,
        )

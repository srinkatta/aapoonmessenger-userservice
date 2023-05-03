import time
import logging
import phonenumbers

from django.db import connections
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from user.api.direct_messages.serializers import (
    NotifyRedirectDmSerializer,
    MuteMessageSerializer,
    ArchiveChatSerializer,
)
from user.models import (
    User,
    MuteCoversation,
)
from user.utils import CustomPagination
from user.helpers import notification
from user_service import settings

logger = logging.getLogger(__name__)


class NotifyRedirectDmViewSet(APIView):
    http_method_names = ["post"]
    serializer_class = NotifyRedirectDmSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        """
        Renamed the field `from` to `from_user` because `from` is a reserved keyword and can't be used a variable
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
                        {"data": "No user found"}, status=status.HTTP_404_NOT_FOUND
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
                        {"data": "No user found"}, status=status.HTTP_404_NOT_FOUND
                    )

                # Check for muted conversation
                if MuteCoversation.objects.filter(
                    sender_id=from_user.id, recipient_id=to_user.id, mute=True
                ).exists():
                    print(time.time())
                    mutify = MuteCoversation.objects.filter(
                        sender_id=from_user.id, recipient_id=to_user.id, mute=True
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
        return Response({"data": "Notification sent."}, status=200)


class MuteMessageView(APIView):
    """
    API View to mute receiving messages from some other user.
    """

    permission_classes = (AllowAny,)
    allowed_methods = ("POST", "GET")
    serializer_class = MuteMessageSerializer

    def get(self, request, *args, **kwargs):
        params = request.GET
        if "mute" in params and "recipient" in params and "sender" in params:
            sender = params.get("sender") + "@" + settings.XMPP_HOST
            recipient = params.get("recipient") + "@" + settings.XMPP_HOST
            message = MuteCoversation.objects.filter(
                sender_id=sender, recipient_id=recipient, mute=True
            )
            serializer = MuteMessageSerializer(message, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {"data": "Field missing in Query params."}, status=status.HTTP_200_OK
        )

    def post(self, request):
        data = request.data
        sender = data.get("sender_id")
        sender = str(sender) + "@" + settings.XMPP_HOST
        recipient = data.get("recipient_id")
        recipient = str(recipient) + "@" + settings.XMPP_HOST
        mute_time = data.get("mute_time")
        mute = data.get("mute")
        if MuteCoversation.objects.filter(
            sender_id=sender, recipient_id=recipient
        ).exists():
            message = MuteCoversation._default_manager.get(
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
    def __init__(self, **kwargs):
        for field in ("id", "bare_peer", "timestamp", "xml", "username", "user_pic"):
            if field in kwargs:
                setattr(self, field, kwargs.get(field))


class XMPPMonthlyChatViewSet(viewsets.ViewSet, CustomPagination):
    permission_classes = [IsAuthenticated]
    serializer_class = ArchiveChatSerializer
    http_method_names = ["get"]

    def fetch_archive_data(self, query, username):
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
        archive_chat = []
        for archive in archive_data:
            # ToDo : test
            user = User.objects.filter(id=archive[-1])
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
            return Response({"data": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def xml_timestamp_value(self, xml):
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml)
        for page in root:
            for time in page:
                if time.tag == "{urn:xmpp:time}Time":
                    epoch_time = time.text
                    return epoch_time


class XMPPDeleteDMViewSet(APIView):
    serializer_class = ArchiveChatSerializer
    http_method_names = ["post"]

    def post(self, request):
        ids = request.data.get("ids", "")
        q = "DELETE FROM archive WHERE id IN " + str(tuple(ids)) + ";"
        try:
            with connections["xmpp_database"].cursor() as cursor:
                cursor.execute(q)
            return Response(
                {"data": "Message deleted Successfully"}, status=status.HTTP_200_OK
            )
        except Exception as e:
            print(e)
            return Response({"data": str(e)}, status=status.HTTP_400_BAD_REQUEST)

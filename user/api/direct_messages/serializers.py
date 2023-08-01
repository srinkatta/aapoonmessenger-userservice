from rest_framework import serializers
from user.models import MuteConversation


class NotifyRedirectDmSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=512)
    xml = serializers.CharField(max_length=256)
    from_user = serializers.CharField(
        max_length=256, label="from"
    )
    to = serializers.CharField(max_length=256)
    vhost = serializers.CharField(max_length=256)
    message_id = serializers.CharField(
        max_length=256, allow_null=True, allow_blank=True
    )


class MuteMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MuteConversation
        fields = "__all__"


class ArchiveChatSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    timestamp = serializers.IntegerField(read_only=True)
    bare_peer = serializers.CharField(max_length=256)
    xml = serializers.CharField(max_length=256)
    username = serializers.CharField(max_length=256)
    user_pic = serializers.URLField(max_length=256)


class UserChatDeleteSerializer(serializers.Serializer):
    sender = serializers.CharField(
        required=True, help_text="Expecting country_code+phone_number of user"
    )
    recipient = serializers.CharField(
        required=True, help_text="Expecting jid of the other user."
    )

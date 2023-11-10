import base64
import uuid
from datetime import datetime, timedelta, timezone

from rest_framework import serializers

from user_service import settings


class S3UploadPolicySerializer(serializers.Serializer):
    def __init__(
        self,
        key="",
        expires_after=timedelta(days=1),
        acl=settings.AWS_S3_ACL,
        success_action_redirect=None,
        content_type=None,
        min_size=0,
        max_size=None,
        feed_obj=False,
        chat_obj=False,
        *args,
        **kwargs
    ):
        self.aws_access_key = settings.S3_AWS_ACCESS_KEY_ID
        self.aws_secret_key = settings.S3_AWS_SECRET_ACCESS_KEY
        self.bucket = settings.AWS_S3_BUCKET_NAME
        self.key = key
        self.expires_after = expires_after
        self.acl = acl
        self.success_action_redirect = success_action_redirect
        self.content_type = content_type
        self.min_size = min_size
        self.max_size = max_size
        self.feed_obj = feed_obj
        self.chat_obj = chat_obj
        super(S3UploadPolicySerializer, self).__init__(*args, **kwargs)

    def to_native(self, obj={}):
        policy = base64.b64encode(bytes(self.calculate_policy(), encoding="utf-8"))
        signature = self.sign_policy(policy)
        expiry_utc = datetime.now(timezone.utc) + self.expires_after
        expiry_str = expiry_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        obj = {
            "key": self.key,
            "AWSAccessKeyId": self.aws_access_key,
            "AWSSecretKey": self.aws_secret_key,
            "AWSS3BucketName": settings.AWS_S3_BUCKET_NAME,
            "acl": self.acl,
            "policy": policy,
            "signature": signature,
            "expiry": expiry_str,
            "epoch_time": int(
                (datetime.now(timezone.utc) + self.expires_after).timestamp()
            ),
            "s3:x-amz-server-side-encryption": "aws:kms",
        }
        if self.success_action_redirect:
            obj["success_action_redirect"] = self.success_action_redirect

        unique_id = str(uuid.uuid1())

        obj["post_action"] = self.post_action()
        return obj

    def calculate_policy(self):
        from json import dumps

        conditions = [
            {"bucket": self.bucket},
            {"acl": self.acl},
            {"success_action_status": "201"},
        ]
        if self.success_action_redirect:
            conditions.append({"success_action_redirect": self.success_action_redirect})
        if self.key.endswith("${filename}"):
            conditions.append(
                ["starts-with", "$key", "%s" % self.key[: -len("${filename}")]]
            )
        else:
            conditions.append({"key": "%s"} % self.key)
        if self.content_type:
            if self.content_type.startswith("image"):
                conditions.append(["starts-with", "$Content-Type", "image/"])
            else:
                conditions.append(
                    ["starts-with", "$Content-Type", "%s" % self.content_type]
                )

        expiry_utc = datetime.now(timezone.utc) + self.expires_after
        expiry_str = expiry_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        policy_document = {
            "expiration": expiry_str,
            "conditions": conditions,
        }
        return dumps(policy_document).replace("\n", "").replace("\r", "")

    def sign_policy(self, policy):
        import hashlib
        import hmac

        signature = hmac.new(
            (bytes(self.aws_secret_key, encoding="utf-8")), policy, hashlib.sha256
        ).hexdigest()
        signature_bytes = bytes.fromhex(signature)

        return base64.b64encode(signature_bytes)

    def post_action(self):
        return "https://%s.s3-accelerate.amazonaws.com/" % settings.AWS_S3_BUCKET_NAME

    perms_map = {
        "GET": {"features": [], "view_perms": []},
    }

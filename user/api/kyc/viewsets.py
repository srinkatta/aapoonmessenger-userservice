import uuid
from urllib.parse import urlparse

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from user.api.kyc.s3uploadserializer import S3UploadPolicySerializer
from user.api.kyc.serializers import (
    SelfieSerializer,
    PhotoIDSerializer,
    ProfileSerializer,
    CompareFacesV2Serializer,
)
from user.utils import s3_url_extract, clear_bucket_from_path


class BaseViewSet(APIView):
    def cloudfront_cdn(self, logo):
        parsed_url = urlparse(logo)
        s3_url = s3_url_extract(logo)
        key = clear_bucket_from_path(parsed_url.path)
        logo = s3_url + key
        return logo


class SelfieViewSet(BaseViewSet):
    """
    API View to Upload Selfie
    """

    serializer_class = SelfieSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        url = serializer.data.get("url")
        serializer.data["url"] = self.cloudfront_cdn(url)

        response = serializer.selfie(request.user)

        if response.get("is_verified"):
            user_kyc_settings = request.user.settings.get()
            user_kyc_settings.selfie = True
            user_kyc_settings.picture = (
                request.data.get("picture") if request.data.get("picture") else False
            )

            request.user.secondary_picture = self.cloudfront_cdn(url)
            user_kyc_settings.save()
            request.user.save()

        return Response(response)


class PhotoIDVerifyViewSet(BaseViewSet):
    """
    API View to verify and compare photo id through OCR
    """

    serializer_class = PhotoIDSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.data["source_key"] = self.cloudfront_cdn(request.data["source_key"])

        serializer = self.serializer_class(request.data)
        response = serializer.photo_id_verification(request.user)

        return Response(response)


class ProfileUpdateViewSet(BaseViewSet):
    """
    API View to Update Profile picture
    """

    serializer_class = ProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        target_key = serializer.data.get("target_key")
        link = self.cloudfront_cdn(target_key)
        serializer.data["target_key"] = self.cloudfront_cdn(target_key)

        serializer = self.serializer_class(request.data)
        response = serializer.profile(request.user)

        if response.get("is_verified"):
            request.user.secondary_picture = self.cloudfront_cdn(link)
            request.user.save()

        return Response(response)


class ComparefacesViewSet(BaseViewSet):
    """
    API View to Compare Face with Selfie and Photo ID
    """

    serializer_class = CompareFacesV2Serializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        link = self.cloudfront_cdn(request.data.get("target_key"))
        serializer.data["source_key"] = self.cloudfront_cdn(request.data["source_key"])
        serializer.data["target_key"] = self.cloudfront_cdn(request.data["target_key"])
        request.data["source_key_back_side"] = (
            self.cloudfront_cdn(request.data["source_key_back_side"])
            if "source_key_back_side" in request.data
            and request.data["source_key_back_side"] != ""
            else ""
        )

        serializer = self.serializer_class(request.data)
        response = serializer.compare_faces(request.user)

        if response.get("is_verified"):
            user_kyc_setting = request.user.settings.get()
            user_kyc_setting.kyc_done = True
            user_kyc_setting.kyc_status = 1
            user_kyc_setting.save()
            request.user.logo = self.cloudfront_cdn(link)
            request.user.save()
        return Response(response)


class KYCUploadViewSet(GenericViewSet):
    serializer_class = S3UploadPolicySerializer
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        key = "kyc/%s/${filename}" % str(uuid.uuid1())
        serializer = self.serializer_class(key=key, content_type="image/png/jpeg/jpg")
        return Response(serializer.to_native())


class FeedbackUploadViewSet(GenericViewSet):
    serializer_class = S3UploadPolicySerializer
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        key = "feedback/%s/${filename}" % str(uuid.uuid1())
        serializer = self.serializer_class(key=key, content_type="image/png/jpeg/jpg")
        return Response(serializer.to_native())

from urllib.parse import urlparse

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from user.api.kyc.s3uploadserializer import S3UploadPolicySerializer
from user.api.kyc.serializers import (
    CompareFacesV2Serializer,
    PhotoIDSerializer,
    ProfileSerializer,
    SelfieSerializer,
)
from user.utils import s3_url_extract, clear_bucket_from_path
from user.api.kyc import services as kyc_service


class BaseViewSet(APIView):
    """
    Base API view with common utilities.

    This base API view provides common utility methods that can be used by other
    API views to perform tasks such as modifying URLs for CloudFront CDN.

    Methods:
    - cloudfront_cdn: Modifies and returns a URL for CloudFront CDN.
    """

    def cloudfront_cdn(self, logo):
        """
        Modify URL for CloudFront CDN.

        This method takes a URL as input and modifies it to include the appropriate
        CloudFront CDN URL if applicable.

        Args:
        - logo (str): The input URL to be modified.

        Returns:
        - str: The modified URL with CloudFront CDN if applicable.
        """
        parsed_url = urlparse(logo)
        s3_url = s3_url_extract(logo)
        key = clear_bucket_from_path(parsed_url.path)
        logo = s3_url + key
        return logo


class SelfieViewSet(BaseViewSet):
    """
    API view for uploading and verifying user selfies.

    This API view allows authenticated users to upload their selfie images and initiate
    the verification process. Uploaded selfies can be verified for authentication purposes.

    Authentication:
    - IsAuthenticated: Users must be authenticated to access this view.

    HTTP Methods:
    - POST: Upload and verify user selfies.

    Request Data (POST):
    - 'url' (str, optional): URL of the uploaded selfie image.
    - 'picture' (bool, optional): Indicates whether the user has uploaded a secondary picture.

    Returns:
    - Response: JSON response indicating the result of the selfie upload and verification process.
    """

    serializer_class = SelfieSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        """
        Upload and verify user selfies.

        This method processes the uploaded selfie image, initiates the verification process,
        and updates the user's selfie and picture settings based on the verification outcome.

        Args:
        - request (Request): The HTTP POST request containing the selfie image and verification data.

        Returns:
        - Response: JSON response indicating the result of the selfie upload and verification process.
        """
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        url = serializer.data.get("url", "")
        request.data["url"] = self.cloudfront_cdn(url) if request.data["url"] else ""

        response = kyc_service.validate_selfie(request.user, request.data["url"])

        if response.get("is_verified"):
            user_kyc_settings = request.user.settings.filter().first()
            user_kyc_settings.selfie = True
            user_kyc_settings.picture = (
                request.data.get("picture") if request.data.get("picture") else False
            )

            request.user.secondary_picture = request.data["url"]
            user_kyc_settings.save()
            request.user.save()

        return Response(response)


class PhotoIDVerifyViewSet(BaseViewSet):
    """
    API view for verifying and comparing photo ID through OCR.

    This API view allows authenticated users to verify and compare photo ID images
    using Optical Character Recognition (OCR) technology. The uploaded photo ID images
    are processed for verification and comparison.

    Authentication:
    - IsAuthenticated: Users must be authenticated to access this view.

    HTTP Methods:
    - POST: Verify and compare photo ID through OCR.

    Request Data (POST):
    - 'source_key' (str): URL of the uploaded photo ID image.

    Returns:
    - Response: JSON response indicating the result of the photo ID verification and comparison.
    """

    serializer_class = PhotoIDSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        """
        Verify and compare photo ID through OCR.

        This method processes the uploaded photo ID image using OCR technology,
        verifies its authenticity, and compares it with the user's photo ID for
        verification purposes.

        Args:
        - request (Request): The HTTP POST request containing the photo ID image URL.

        Returns:
        - Response: JSON response indicating the result of the photo ID verification and comparison.
        """
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        request.data["source_key"] = self.cloudfront_cdn(request.data["source_key"])

        response = kyc_service.validate_and_compare_photo_id(
            request.user,
            request.data["source_key"],
        )

        return Response(response)


class ProfileUpdateViewSet(BaseViewSet):
    """
    API view for updating user profile picture.

    This API view allows authenticated users to update their profile pictures.
    The uploaded profile pictures can be verified and updated in the user's profile.

    Authentication:
    - IsAuthenticated: Users must be authenticated to access this view.

    HTTP Methods:
    - POST: Update user profile picture.

    Request Data (POST):
    - 'target_key' (str, optional): URL of the uploaded profile picture.

    Returns:
    - Response: JSON response indicating the result of the profile picture update.
    """

    serializer_class = ProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        """
        Update user profile picture.

        This method processes the uploaded profile picture, initiates the verification process,
        and updates the user's profile picture based on the verification outcome.

        Args:
        - request (Request): The HTTP POST request containing the profile picture URL.

        Returns:
        - Response: JSON response indicating the result of the profile picture update.
        """
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        target_key = serializer.data.get("target_key", "")

        request.data["target_key"] = (
            self.cloudfront_cdn(target_key) if target_key else ""
        )

        response = kyc_service.update_profile_picture(
            request.user, request.data["target_key"]
        )

        if response.get("is_verified"):
            request.user.secondary_picture = request.data["target_key"]
            request.user.save()

        return Response(response)


class ComparefacesViewSet(BaseViewSet):
    """
    API view for comparing a face with selfie and photo ID.

    This API view allows authenticated users to compare a facial image with a selfie and
    a photo ID image. The uploaded images are processed for facial comparison and verification.

    Authentication:
    - IsAuthenticated: Users must be authenticated to access this view.

    HTTP Methods:
    - POST: Compare a face with selfie and photo ID.

    Request Data (POST):
    - 'source_key' (str): URL of the source facial image.
    - 'target_key' (str): URL of the target selfie image.
    - 'source_key_back_side' (str, optional): URL of the back side of the source ID image.

    Returns:
    - Response: JSON response indicating the result of the facial comparison and verification.
    """

    serializer_class = CompareFacesV2Serializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        """
        Compare a face with selfie and photo ID.

        This method processes the uploaded facial, selfie, and photo ID images,
        performs facial comparison, and verifies the user's identity based on the comparison.

        Args:
        - request (Request): The HTTP POST request containing the image URLs.

        Returns:
        - Response: JSON response indicating the result of the facial comparison and verification.
        """
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        link = self.cloudfront_cdn(request.data.get("target_key"))
        request.data["source_key"] = self.cloudfront_cdn(request.data["source_key"])
        request.data["target_key"] = self.cloudfront_cdn(request.data["target_key"])

        request.data["source_key_back_side"] = (
            self.cloudfront_cdn(request.data["source_key_back_side"])
            if request.data.get("source_key_back_side")
            else ""
        )

        response = kyc_service.compare_faces(request.user, request.data)

        if response.get("is_verified"):
            user_kyc_setting = request.user.settings.filter().first()
            user_kyc_setting.kyc_done = True
            user_kyc_setting.kyc_status = 1
            user_kyc_setting.save()
            request.user.logo = self.cloudfront_cdn(link)
            request.user.save()
        return Response(response)


class KYCUploadViewSet(GenericViewSet):
    """
    API view for providing S3 upload policy for KYC document.

    This API view allows authenticated users to obtain an S3 upload policy
    for uploading KYC (Know Your Customer) documents.

    Authentication:
    - IsAuthenticated: Users must be authenticated to access this view.

    HTTP Methods:
    - GET: Obtain S3 upload policy for KYC document.

    Returns:
    - Response: JSON response containing the S3 upload policy for KYC document.
    """

    serializer_class = S3UploadPolicySerializer
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        """
        Obtain S3 upload policy for KYC document.

        This method generates an S3 upload policy for authenticated users
        to upload KYC documents to Amazon S3 storage.

        Args:
        - request (Request): The HTTP GET request.

        Returns:
        - Response: JSON response containing the S3 upload policy for KYC document.
        """
        key = "%s/kyc/${filename}" % request.user.unique_id
        serializer = self.serializer_class(key=key, content_type="image/png/jpeg/jpg")
        return Response(serializer.to_native())


class FeedbackUploadViewSet(GenericViewSet):
    """
    API view for providing S3 upload policy for feedback images.

    This API view allows authenticated users to obtain an S3 upload policy
    for uploading images related to user feedback.

    Authentication:
    - IsAuthenticated: Users must be authenticated to access this view.

    HTTP Methods:
    - GET: Obtain S3 upload policy for feedback images.

    Returns:
    - Response: JSON response containing the S3 upload policy for feedback images.
    """

    serializer_class = S3UploadPolicySerializer
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        """
        Obtain S3 upload policy for feedback attachments.

        This method generates an S3 upload policy for authenticated users
        to upload attachments to user feedback.

        Args:
        - request (Request): The HTTP GET request.

        Returns:
        - Response: JSON response containing the S3 upload policy for feedback attachments.
        """
        key = "%s/feedback/${filename}" % request.user.unique_id
        serializer = self.serializer_class(key=key, content_type="image/png/jpeg/jpg")
        return Response(serializer.to_native())

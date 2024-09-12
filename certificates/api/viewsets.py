from typing import Optional

from django.core.files.base import ContentFile
from django.http import FileResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from certificates.api import serializers as certificate_serializers
from certificates import models as certificates_models
from certificates.utils import sign_certificate
from certificates.utils import upload_sign_certificate
import tempfile
import os


class SignCertificateAPIView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="device_id",
                description="The ID of the device",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
            )
        ],
        responses={200: certificate_serializers.CertificateSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        serializer = certificate_serializers.DeviceIDSerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        device_id = serializer.validated_data["device_id"]

        queryset = certificates_models.Certificate.objects.filter(device=device_id)

        serialized_data = certificate_serializers.CertificateSerializer(
            queryset, many=True
        ).data

        return Response(serialized_data, status=status.HTTP_200_OK)

    @extend_schema(
        request=certificate_serializers.CertificateSerializer,
        responses={201: certificate_serializers.CertificateSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = certificate_serializers.CertificateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        csr_content = serializer.validated_data["csr_certificate"]
        device_id = serializer.validated_data["device"]
        phone_number = serializer.validated_data.get("phone_number")

        signer = sign_certificate.CertificateSigner()
        uploader = upload_sign_certificate.S3Uploader()

        try:
            signed_certificate = signer.sign_certificate(csr_content)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".csr") as temp_file:
                temp_file.write(signed_certificate.encode("utf-8"))
                temp_file_path = temp_file.name

            signed_certificate_link = uploader.upload_file(
                file_path=temp_file_path,
                s3_key_suffix=f"signed_certificate_{device_id}.crt",
            )

            # save certificate in db
            certificate = self.__save_certificate(
                csr_content=csr_content,
                device_id=device_id,
                phone_number=phone_number,
                signed_certificate_link=signed_certificate_link,
            )

            return Response(
                certificate_serializers.CertificateSerializer(certificate).data,
                status=status.HTTP_201_CREATED,
            )

        except RuntimeError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        finally:
            if temp_file_path and os.path.isfile(temp_file_path):
                os.remove(temp_file_path)

    def __save_certificate(
        self,
        csr_content: str,
        device_id: str,
        phone_number: Optional[str],
        signed_certificate_link: Optional[str],
    ) -> certificates_models.Certificate:
        certificate, _ = certificates_models.Certificate.objects.get_or_create(
            csr_certificate=csr_content,
            device=device_id,
        )
        certificate.phone_number = phone_number
        certificate.signed_certificate = signed_certificate_link
        certificate.save()
        return certificate

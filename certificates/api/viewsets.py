from django.core.files.base import ContentFile
from django.http import FileResponse
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from certificates.api import serializers as certificate_serializers
from certificates import models as certificates_models
from certificates.utils import sign_certificate


class SignCertificateAPIView(APIView):
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

    def post(self, request, *args, **kwargs):
        serializer = certificate_serializers.CertificateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        csr_certificate_file = request.FILES.get("csr_certificate")
        device_id = serializer.validated_data["device"]
        phone_number = serializer.validated_data.get("phone_number")

        signer = sign_certificate.CertificateSigner()

        try:
            csr_content = csr_certificate_file.read().decode("utf-8")
            signed_certificate = signer.sign_certificate(csr_content)
            signed_certificate_file = ContentFile(
                signed_certificate.encode("utf-8"), f"signed_certificate{device_id}.pem"
            )

        except RuntimeError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        certificates_models.Certificate.objects.create(
            csr_certificate=csr_content,
            device=device_id,
            phone_number=phone_number,
            signed_certificate=signed_certificate_file,
        )

        response = FileResponse(
            signed_certificate_file,
            as_attachment=True,
            filename="signed_certificate.pem",
            content_type="application/x-x509-ca-cert",
        )

        return response

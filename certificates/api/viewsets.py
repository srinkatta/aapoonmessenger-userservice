from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from certificates.api import serializers as certificate_serializers
from certificates import models as certificates_models
import subprocess
from user_service import settings


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

        csr_certificate = serializer.validated_data["csr_certificate"]
        device_id = serializer.validated_data["device"]
        phone_number = serializer.validated_data.get("phone_number")

        try:
            signed_certificate = self.sign_certificate(csr_certificate)
        except RuntimeError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        certificate_instance = certificates_models.Certificate.objects.create(
            csr_certificate=csr_certificate,
            device_id=device_id,
            phone_number=phone_number,
            signed_certificate=signed_certificate,
        )

        serialized_certificate_instance = certificate_serializers.CertificateSerializer(
            certificate_instance
        ).data

        return Response(serialized_certificate_instance, status=status.HTTP_201_CREATED)

    def sign_certificate(self, csr_certificate):
        """
        Sign the CSR certificate using OpenSSL with the CA certificate and key.

        Args:
            csr_certificate_path (str): Path to the CSR file to be signed.

        Returns:
            str: The signed certificate in PEM format.

        Raises:
            RuntimeError: If the certificate signing process fails.
        """
        ca_certificate = settings.CA_CERTIFICATE
        ca_key = settings.CA_KEY
        signed_certificate_path = "signed_certificate.pem"

        openssl_command = [
            "openssl",
            "x509",
            "-req",
            "-in",
            csr_certificate,
            "-CA",
            ca_certificate,
            "-CAkey",
            ca_key,
            "-CAcreateserial",
            "-out",
            signed_certificate_path,
            "-days",
            "365",
            "-sha256",
        ]

        try:
            result = subprocess.run(
                openssl_command, check=True, capture_output=True, text=True
            )
            print(
                f"CSR signed successfully. Signed certificate saved to: {signed_certificate_path}"
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to sign certificate: {e.stderr}")

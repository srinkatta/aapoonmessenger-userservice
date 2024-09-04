from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from certificates.api import serializers as certificate_serializers
import subprocess


class SignCertificateAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = certificate_serializers.CertificateSerializer(data=request.data)
        if serializer.is_valid():
            csr_certificate = serializer.validated_data["csr_certificate"]
            device_id = serializer.validated_data["device_id"]
            phone_number = serializer.validated_data.get("phone_number")
            # Sign the CSR using OpenSSL with post-quantum cryptography
            signed_certificate = self.sign_certificate(csr_certificate)
            # Save the signed certificate and other details in the database
            certificate = certificate_serializers.Certificate.objects.create(
                csr_certificate=csr_certificate,
                device_id=device_id,
                phone_number=phone_number,
                signed_certificate=signed_certificate,
            )
            return Response(
                certificate_serializers.CertificateSerializer(certificate).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def sign_certificate(self, csr_certificate):
        # Use OpenSSL to sign the CSR certificate with CA certificate
        # You need to replace the following with your actual command to sign the CSR
        # For post-quantum cryptography, use relevant algorithms like Dilithium, Falcon, or Kyber
        ca_certificate = "/path/to/ca_certificate.pem"
        ca_key = "/path/to/ca_key.pem"
        process = subprocess.Popen(
            [
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
                "-",
                "-days",
                "365",
                "-sha256",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise Exception(f"Failed to sign certificate: {stderr.decode()}")
        return stdout.decode()

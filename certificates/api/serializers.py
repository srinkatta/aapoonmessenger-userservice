from rest_framework import serializers
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.x509.oid import NameOID
from certificates import models as certificate_models


class CertificateSerializer(serializers.ModelSerializer):
    """
    Serializer for Certificate Signing Requests (CSRs).
    """

    class Meta:
        model = certificate_models.Certificate
        fields = "__all__"
        read_only_fields = ["csr_certificate", "created_at"]

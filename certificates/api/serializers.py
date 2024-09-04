from rest_framework import serializers
from certificates import models as certificate_models


class CertificateSerializer(serializers.ModelSerializer):
    """
    Serializer for Certificate Signing Requests (CSRs).
    """

    class Meta:
        model = certificate_models.Certificate
        fields = "__all__"
        read_only_fields = ["csr_certificate", "created_at"]

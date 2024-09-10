from rest_framework import serializers
from certificates import models as certificate_models
from certificates.utils import validators as certificate_validators


class CertificateSerializer(serializers.ModelSerializer):
    """
    Serializer for Certificate Signing Requests (CSRs).
    """

    csr_certificate = serializers.FileField(
        validators=[certificate_validators.CertificateExtensionValidator()]
    )

    class Meta:
        model = certificate_models.Certificate
        fields = "__all__"


class DeviceIDSerializer(serializers.Serializer):
    device_id = serializers.CharField()

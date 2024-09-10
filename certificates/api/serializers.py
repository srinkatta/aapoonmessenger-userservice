from rest_framework import serializers
from certificates import models as certificate_models


class CertificateSerializer(serializers.ModelSerializer):
    """
    Serializer for Certificate Signing Requests (CSRs).
    """

    csr_certificate = serializers.FileField()

    class Meta:
        model = certificate_models.Certificate
        fields = "__all__"


class DeviceIDSerializer(serializers.Serializer):
    device_id = serializers.CharField()

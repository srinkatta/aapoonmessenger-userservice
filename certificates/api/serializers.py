from rest_framework import serializers
from certificates import models as certificate_models
from certificates.utils import validators as certificate_validators


class CSRFileField(serializers.Field):
    """
    Custom field to handle CSR file uploads.
    Accepts .csr files, validates them, and reads their contents as text.
    """

    def to_internal_value(self, data):
        # Check that data is a file and has the correct extension
        if not hasattr(data, "read"):
            raise serializers.ValidationError("This field expects a file.")

        if not data.name.endswith(".csr"):
            raise serializers.ValidationError("Only .csr files are allowed.")

        try:
            # Read file content and decode it to utf-8
            return data.read().decode("utf-8")
        except Exception as e:
            raise serializers.ValidationError(f"Error reading file: {str(e)}")

    def to_representation(self, value):
        return value


class CertificateSerializer(serializers.ModelSerializer):
    """
    Serializer for Certificate Signing Requests (CSRs).
    Accepts csr_certificate as a file input but stores it as text (PEM format) in the model.
    """

    csr_certificate = CSRFileField(write_only=True)

    class Meta:
        model = certificate_models.Certificate
        fields = ["device", "phone_number", "csr_certificate", "signed_certificate"]


class DeviceIDSerializer(serializers.Serializer):
    device_id = serializers.CharField()

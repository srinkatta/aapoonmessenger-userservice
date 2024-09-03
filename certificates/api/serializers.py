from rest_framework import serializers
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.x509.oid import NameOID
from certificates import models as certificate_models


class CSRSerializer(serializers.ModelSerializer):
    """
    Serializer for Certificate Signing Requests (CSRs).

    This serializer handles the creation of CSRs, including generating the
    private key and CSR certificate.

    Attributes:
        device (ForeignKey): Reference to the UserDevice model.
        phone_number (CharField): Optional phone number associated with the CSR.
        csr_certificate (TextField): Required CSR data in PEM format.
        sound_certificate (TextField): Optional sound certificate data in PEM format.
        created_at (DateTimeField): Timestamp of when the CSR was created.

    Methods:
        create(validated_data):
            Generates a private key and CSR, and saves them to the database.
    """

    class Meta:
        model = certificate_models.CSR
        fields = "__all__"
        read_only_fields = ["csr_certificate", "created_at"]

    def create(self, validated_data):
        device = validated_data.get("device")
        phone_number = validated_data.get("phone_number")

        # TODO: Replace RSA with Kyber512 as Required
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Create CSR
        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(
                x509.Name(
                    [
                        x509.NameAttribute(NameOID.COMMON_NAME, str(device)),
                        x509.NameAttribute(NameOID.SERIAL_NUMBER, str(phone_number)),
                    ]
                )
            )
            .sign(private_key, hashes.SHA256())
        )

        csr_pem = csr.public_bytes(serialization.Encoding.PEM)

        # Create CSR instance
        csr_instance = certificate_models.CSR.objects.create(
            device=device,
            phone_number=phone_number,
            csr_certificate=csr_pem.decode("utf-8"),
        )

        return csr_instance

from django.db import models
from common import models as common_models
from certificates.utils import validators as certificate_validators


class Certificate(common_models.BaseTimeStampedModel):
    """
    Model to store Certificate Signing Requests (CSRs) related to user devices.

    Attributes:
        device (CharField): Device details.
        phone_number (CharField): Optional phone number associated with the CSR.
        csr_certificate (TextField): Required CSR data in PEM format.
        signed_certificate (FileField): Optional signed certificate data in PEM format.
    """

    device = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    csr_certificate = models.TextField()
    signed_certificate = models.FileField(
        upload_to="signed_certificates/",
        blank=True,
        null=True,
        validators=[certificate_validators.CertificateExtensionValidator()],
    )

    def __str__(self):
        return f"CSR for Device {self.device}"

    class Meta:
        verbose_name = "CSR Certificate"
        verbose_name_plural = "CSR Certificates"
        ordering = ["-created_at"]

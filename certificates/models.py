from django.db import models
from common import models as common_models


class Certificate(common_models.BaseTimeStampedModel):
    """
    Model to store Certificate Signing Requests (CSRs) related to user devices.

    Attributes:
        device (CharField): Device details.
        phone_number (CharField): Optional phone number associated with the CSR.
        csr_certificate (TextField): Required CSR data in PEM format.
        signed_certificate (TextField): Optional signed certificate data in PEM format.
    """

    device = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    csr_certificate = models.TextField()
    signed_certificate = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"CSR for Device {self.device}"

    class Meta:
        verbose_name = "CSR Certificate"
        verbose_name_plural = "CSR Certificates"
        ordering = ["-created_at"]

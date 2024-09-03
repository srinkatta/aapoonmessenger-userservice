from django.db import models
from common import models as common_models
from user import models as user_models


class CSR(common_models.BaseTimeStampedModel):
    """
    Model to store Certificate Signing Requests (CSRs) related to user devices.

    Attributes:
        device (ForeignKey): Reference to the UserDevice model.
        phone_number (CharField): Optional phone number associated with the CSR.
        csr_certificate (TextField): Required CSR data in PEM format.
        sound_certificate (TextField): Optional sound certificate data in PEM format.
    """

    device = models.ForeignKey(
        user_models.UserDevice,
        on_delete=models.CASCADE,
        related_name="csr_devices",
    )
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    csr_certificate = models.TextField()
    sound_certificate = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"CSR for Device {self.device}"

    class Meta:
        verbose_name = "CSR"
        verbose_name_plural = "CSRs"
        ordering = ["-created_at"]

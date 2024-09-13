from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
import os
from certificates.utils import constants


@deconstructible
class CertificateExtensionValidator:
    def __init__(self, valid_extensions=None):
        self.valid_extensions = (
            valid_extensions or constants.VALID_CERTIFICATE_EXTENSIONS
        )

    def __call__(self, value):
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in self.valid_extensions:
            raise ValidationError(
                f'Unsupported file extension. Allowed extensions are: {", ".join(self.valid_extensions)}'
            )

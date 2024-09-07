from django.contrib import admin
from certificates import models as certificate_models

admin.site.register(certificate_models.Certificate)

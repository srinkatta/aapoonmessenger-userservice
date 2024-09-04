from django.urls import path
from certificates.api import viewsets as certificate_viewsets


urlpatterns = [
    path(
        "csrs/",
        certificate_viewsets.SignCertificateAPIView.as_view(),
        name="sign-certificate",
    ),
]

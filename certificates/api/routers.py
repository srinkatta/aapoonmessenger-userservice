from django.urls import path, include
from rest_framework.routers import DefaultRouter
from certificates.api import viewsets as certificate_viewsets

router = DefaultRouter()
router.register(r"csrs", certificate_viewsets.CSRViewSet, basename="csr")

urlpatterns = [
    path("", include(router.urls)),
]

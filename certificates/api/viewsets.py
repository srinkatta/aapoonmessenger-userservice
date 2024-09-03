from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from certificates import models as certificate_models
from certificates.api import serializers as certificate_serializers


class CSRViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling Certificate Signing Requests (CSRs).

    This ViewSet provides actions to list, retrieve, create, update, and delete CSRs.
    It restricts access to authenticated users and ensures users can only interact with
    their own CSRs.

    Attributes:
        queryset (QuerySet): Default queryset for the viewset, fetching all CSR objects.
        serializer_class (Serializer): Serializer class used to validate and deserialize
            input and serialize output.
        permission_classes (list): List of permission classes to apply to the viewset.

    Methods:
        get_queryset():
            Filters the queryset to only include CSRs related to the authenticated user.
    """

    queryset = certificate_models.CSR.objects.all()
    serializer_class = certificate_serializers.CSRSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filters the queryset to only include CSRs related to the authenticated user.

        Returns:
            QuerySet: Filtered queryset of CSRs for the authenticated user.
        """
        return self.queryset.filter(device__user=self.request.user)

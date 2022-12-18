from django.db import models


class BaseTimeStampedModel(models.Model):
    """
    Abstract model that contains created_at, updated_at
    To be inherited by all other models
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

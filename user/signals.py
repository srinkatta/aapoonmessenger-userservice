from django.db.models.signals import post_save
from django.dispatch import receiver

from user.models import User, UserVerificationSetting, UserProfile, UserLog


@receiver(post_save, sender=User)
def user_kyc_profile_settings(sender, instance, created=False, **kwargs):
    """
    Signal handler for initializing User KYC profile settings.

    Creates user log, profile, and verification settings on user creation.

    Args:
        sender: The sender model class (User).
        instance: The saved User instance.
        created: True if the instance was just created.

    Returns:
        None
    """
    if created:
        UserLog.objects.create(user=instance)
        UserProfile.objects.create(user=instance)
        UserVerificationSetting.objects.create(user=instance, photo_id="0")

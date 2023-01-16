from django.db.models.signals import post_save
from django.dispatch import receiver

from user.models import User, UserVerificationSetting, UserProfile, UserLog


@receiver(post_save, sender=User)
def user_kyc_profile_settings(sender, instance, created=False, **kwargs):
    """ """
    if created:
        UserLog.objects.create(user=instance)
        UserProfile.objects.create(user=instance)
        UserVerificationSetting.objects.create(user=instance, photo_id="0")

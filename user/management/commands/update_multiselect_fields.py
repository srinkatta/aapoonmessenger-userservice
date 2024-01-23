from django.core.management.base import BaseCommand

from user.models import UserProfile


class Command(BaseCommand):
    help = "Update old users multiselect fields list datatype to string datatype for User Profile"

    def handle(self, **options):
        profiles = UserProfile.objects.all()
        for profile in profiles:
            try:
                profile.sports = ",".join(profile.sports) if profile.sports else None
                profile.interests = (
                    ",".join(profile.interests) if profile.interests else None
                )
                profile.education = (
                    ",".join(profile.education) if profile.education else None
                )
                profile.save()
            except Exception as exc:
                print(
                    "An error occurred while updating User Profile's columns: %s", exc
                )

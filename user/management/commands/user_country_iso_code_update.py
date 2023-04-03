from django.core.management.base import BaseCommand
from user.models import User
from user.utils import get_data_from_choices
from user.choices import COUNTRY_CODE_CHOICES


class Command(BaseCommand):
    help = "old users country iso code update"

    def handle(self, **options):
        users = User.objects.all()
        for user in users:
            if user.country_code == "91" or user.country_code == "1":
                try:
                    country = get_data_from_choices(
                        user.country_code, COUNTRY_CODE_CHOICES
                    )
                    user.country_iso_code = country
                    user.save()
                except Exception as e:
                    print("Unexpected error updating user country ISO code: %s", str(e))

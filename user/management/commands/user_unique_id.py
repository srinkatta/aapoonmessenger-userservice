import uuid

from django.core.management.base import BaseCommand

from user.models import User


class Command(BaseCommand):
    help = "Generating old Users unique ID"

    def handle(self, **options):

        users = User.objects.all()
        for user in users:
            unique_id = uuid.uuid4().hex
            while User.objects.filter(unique_id=unique_id).exists():
                unique_id = uuid.uuid4().hex
            user.unique_id = unique_id
        User.objects.bulk_update(users, ["unique_id"])

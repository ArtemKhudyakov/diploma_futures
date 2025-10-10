import os

from django.core.management import BaseCommand
from dotenv import load_dotenv

from ...models import User

load_dotenv(override=True)


class Command(BaseCommand):
    def handle(self, *args, **options):
        user = User.objects.create_superuser(username=os.getenv("ADMIN_USERNAME"), email=os.getenv("ADMIN_EMAIL"))

        user.set_password(os.getenv("ADMIN_PASSWORD"))
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save()

from django.core.management.base import BaseCommand, CommandError
from accounts.models import User


class Command(BaseCommand):
    help = "Give an existing account the WeFiles Admin role; Django staff privileges remain separate."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        updated = User.objects.filter(username=options["username"]).update(role=User.Role.ADMIN)
        if not updated:
            raise CommandError("No account matches that username.")
        self.stdout.write(self.style.SUCCESS("WeFiles Admin role assigned."))

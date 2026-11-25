from django.core.management.base import BaseCommand, CommandError
from django.db.models import F
from accounts.models import User


class Command(BaseCommand):
    help = "Approve, activate and promote an existing workspace Admin; no Django staff privileges are granted."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        updated = User.objects.filter(username=options["username"]).update(
            role=User.Role.ADMIN, account_status=User.AccountStatus.APPROVED,
            is_active=True, session_version=F("session_version") + 1,
        )
        if not updated:
            raise CommandError("No account matches that username.")
        self.stdout.write(self.style.SUCCESS("WeFiles Admin approved and activated. Sign in again to continue."))

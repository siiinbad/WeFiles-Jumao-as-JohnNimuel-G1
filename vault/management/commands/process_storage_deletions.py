from django.core.management.base import BaseCommand

from vault.services import process_deletions


class Command(BaseCommand):
    help = "Retry cleanup for private files removed from the vault."

    def handle(self, *args, **options):
        done, failed = process_deletions()
        self.stdout.write(f"Deleted {done} stored file(s); {failed} cleanup job(s) will retry.")

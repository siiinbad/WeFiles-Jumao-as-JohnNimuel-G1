from django.core.management.base import BaseCommand, CommandError

from vault.services import process_deletions


class Command(BaseCommand):
    help = "Retry cleanup for private files removed from the vault."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=100,
            help="Maximum number of due cleanup jobs to process (default: 100).",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit < 1:
            raise CommandError("--limit must be a positive integer.")
        done, failed = process_deletions(limit=limit)
        self.stdout.write(f"Deleted {done} stored file(s); {failed} cleanup job(s) will retry.")

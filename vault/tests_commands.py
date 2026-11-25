"""Exercise the cleanup command used by Render's startup script."""
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from .models import StorageDeletionJob


class StorageCleanupCommandTests(SimpleTestCase):
    def test_render_startup_arguments_are_accepted(self):
        output = StringIO()
        with patch("vault.management.commands.process_storage_deletions.process_deletions", return_value=(2, 1)) as process:
            call_command("process_storage_deletions", "--limit", "100", stdout=output)
        process.assert_called_once_with(limit=100)
        self.assertIn("Deleted 2 stored file(s); 1 cleanup job(s) will retry.", output.getvalue())

    def test_default_batch_size_preserves_existing_command_usage(self):
        with patch("vault.management.commands.process_storage_deletions.process_deletions", return_value=(0, 0)) as process:
            call_command("process_storage_deletions", stdout=StringIO())
        process.assert_called_once_with(limit=100)

    def test_custom_limit_is_forwarded(self):
        with patch("vault.management.commands.process_storage_deletions.process_deletions", return_value=(0, 0)) as process:
            call_command("process_storage_deletions", "--limit", "7", stdout=StringIO())
        process.assert_called_once_with(limit=7)

    def test_nonpositive_limits_are_rejected_before_processing(self):
        with patch("vault.management.commands.process_storage_deletions.process_deletions") as process:
            for value in ("0", "-1"):
                with self.subTest(limit=value), self.assertRaisesMessage(CommandError, "positive integer"):
                    call_command("process_storage_deletions", "--limit", value, stdout=StringIO())
        process.assert_not_called()

    def test_nonnumeric_limit_is_rejected_before_processing(self):
        with patch("vault.management.commands.process_storage_deletions.process_deletions") as process:
            with self.assertRaises(CommandError):
                call_command("process_storage_deletions", "--limit", "invalid", stdout=StringIO())
        process.assert_not_called()


class StorageCleanupBatchTests(TestCase):
    def test_command_processes_only_the_requested_number_of_jobs(self):
        first = StorageDeletionJob.objects.create(storage_key="objects/first")
        second = StorageDeletionJob.objects.create(storage_key="objects/second")
        output = StringIO()
        with patch("vault.services.default_storage.delete") as delete:
            call_command("process_storage_deletions", "--limit", "1", stdout=output)
        delete.assert_called_once_with(first.storage_key)
        self.assertFalse(StorageDeletionJob.objects.filter(pk=first.pk).exists())
        self.assertTrue(StorageDeletionJob.objects.filter(pk=second.pk).exists())
        self.assertIn("Deleted 1 stored file(s); 0 cleanup job(s) will retry.", output.getvalue())

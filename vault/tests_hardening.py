"""Regression tests for stale records and the service authorization boundary."""
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from accounts.models import User
from .models import Folder, VaultFile
from .services import delete_file, delete_folder, save_folder, update_file, upload_file


class VaultServiceHardeningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="owner", email="owner@example.test")
        cls.other = User.objects.create_user(username="other", email="other@example.test")

    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        storage = override_settings(MEDIA_ROOT=media.name)
        storage.enable()
        self.addCleanup(storage.disable)

    def upload(self):
        return upload_file(self.owner, SimpleUploadedFile("notes.txt", b"private contents"))

    def test_edit_of_deleted_file_reports_validation_error_without_recreating_it(self):
        file = self.upload()
        VaultFile.objects.filter(pk=file.pk).delete()
        file.name = "stale rename.txt"
        with self.assertRaisesMessage(ValidationError, "already deleted"):
            update_file(self.owner, file)
        self.assertFalse(VaultFile.objects.exists())

    def test_repeated_file_delete_reports_validation_error(self):
        file = self.upload()
        delete_file(self.owner, file)
        with self.assertRaisesMessage(ValidationError, "already deleted"):
            delete_file(self.owner, file)

    def test_edit_of_deleted_folder_cannot_resurrect_it(self):
        folder = Folder.objects.create(owner=self.owner, name="Original")
        Folder.objects.filter(pk=folder.pk).delete()
        folder.name = "Stale rename"
        with self.assertRaisesMessage(ValidationError, "already deleted"):
            save_folder(self.owner, folder)
        self.assertFalse(Folder.objects.exists())

    def test_repeated_folder_delete_reports_validation_error(self):
        folder = Folder.objects.create(owner=self.owner, name="Original")
        delete_folder(self.owner, folder)
        with self.assertRaisesMessage(ValidationError, "already deleted"):
            delete_folder(self.owner, folder)

    def test_file_is_rechecked_after_waiting_for_owner_lock(self):
        from .services import lock_owner

        file = self.upload()
        file.name = "stale rename.txt"

        def competing_delete(user, owner_id):
            VaultFile.objects.filter(pk=file.pk).delete()
            lock_owner(user, owner_id)

        with patch("vault.services.lock_owner", side_effect=competing_delete):
            with self.assertRaisesMessage(ValidationError, "already deleted"):
                update_file(self.owner, file)
        # This injected delete shares the service transaction and rolls back
        # with the error. The submitted rename must not be persisted.
        file.refresh_from_db()
        self.assertEqual(file.name, "notes.txt")

    def test_file_service_ignores_forged_owner_and_preserves_stored_owner(self):
        file = self.upload()
        file.owner = self.other
        file.name = "Renamed.txt"
        update_file(self.owner, file)
        file.refresh_from_db()
        self.assertEqual(file.owner, self.owner)
        self.assertEqual(file.name, "Renamed.txt")

    def test_other_member_cannot_bypass_view_to_call_mutation_services(self):
        file = self.upload()
        folder = Folder.objects.create(owner=self.owner, name="Private")
        for service, item in (
            (update_file, file), (delete_file, file),
            (save_folder, folder), (delete_folder, folder),
        ):
            with self.subTest(service=service.__name__), self.assertRaises(PermissionDenied):
                service(self.other, item)
        self.assertTrue(VaultFile.objects.filter(pk=file.pk).exists())
        self.assertTrue(Folder.objects.filter(pk=folder.pk).exists())

    def test_invalid_metadata_is_rejected_before_writing_upload_bytes(self):
        with patch("django.core.files.storage.FileSystemStorage._save") as store:
            with self.assertRaises(ValidationError):
                upload_file(
                    self.owner, SimpleUploadedFile("notes.txt", b"private contents"),
                    description="x" * 1001,
                )
        store.assert_not_called()
        self.assertFalse(VaultFile.objects.exists())

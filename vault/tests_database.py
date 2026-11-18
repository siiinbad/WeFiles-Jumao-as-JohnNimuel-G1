import os
from tempfile import TemporaryDirectory
from unittest import skipUnless
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from .models import Folder, StorageDeletionJob, VaultFile
from .services import process_deletions


@skipUnless(os.getenv("TEST_DATABASE_URL"), "Requires a disposable PostgreSQL TEST_DATABASE_URL")
class VaultJourneyTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="fileowner", email="owner@example.test", password="A-long-test-password!374")
        self.other = User.objects.create_user(username="othermember", email="other@example.test", password="A-long-test-password!374")
        self.admin = User.objects.create_user(username="vaultadmin", email="admin@example.test", password="A-long-test-password!374", role=User.Role.ADMIN)
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.storage = override_settings(MEDIA_ROOT=self.media.name)
        self.storage.enable()
        self.addCleanup(self.storage.disable)
        self.client.force_login(self.owner)

    def upload(self, folder=None):
        data = {"file": SimpleUploadedFile("guide.txt", b"private file contents"), "description": "A useful guide"}
        if folder:
            data["folder"] = str(folder.pk)
        response = self.client.post(reverse("vault:upload"), data)
        self.assertEqual(response.status_code, 302)
        return VaultFile.objects.get(name="guide.txt")

    def test_member_can_complete_file_crud_and_download(self):
        file = self.upload()
        self.assertEqual(file.owner, self.owner)
        self.assertContains(self.client.get(reverse("vault:list")), "guide.txt")
        self.assertContains(self.client.get(reverse("vault:detail", args=[file.pk])), "A useful guide")
        response = self.client.get(reverse("vault:download", args=[file.pk]))
        self.assertEqual(b"".join(response.streaming_content), b"private file contents")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("no-store", response["Cache-Control"])
        folder = Folder.objects.create(owner=self.owner, name="Guides")
        response = self.client.post(reverse("vault:edit", args=[file.pk]), {"name": "renamed.txt", "description": "Updated", "folder": str(folder.pk), "owner": self.other.pk})
        self.assertRedirects(response, reverse("vault:detail", args=[file.pk]))
        file.refresh_from_db()
        self.assertEqual((file.name, file.description, file.folder, file.owner), ("renamed.txt", "Updated", folder, self.owner))
        key = file.blob.name
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("vault:delete", args=[file.pk]), {"confirm": "yes"})
        self.assertRedirects(response, reverse("vault:list"))
        self.assertFalse(VaultFile.objects.filter(pk=file.pk).exists())
        self.assertFalse(file.blob.storage.exists(key))
        self.assertFalse(StorageDeletionJob.objects.filter(storage_key=key).exists())

    def test_other_member_cannot_list_read_download_edit_or_delete(self):
        file = self.upload()
        folder = Folder.objects.create(owner=self.owner, name="Secret folder")
        self.client.force_login(self.other)
        listing = self.client.get(reverse("vault:list"))
        self.assertNotContains(listing, file.name)
        self.assertNotContains(listing, folder.name)
        for route in ("detail", "download", "edit", "delete"):
            with self.subTest(route=route):
                url = reverse("vault:" + route, args=[file.pk])
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url, {"name": "stolen.txt", "confirm": "yes"}).status_code in (404, 405), True)
        for route in ("folder", "folder_edit", "folder_delete"):
            self.assertEqual(self.client.get(reverse("vault:" + route, args=[folder.pk])).status_code, 404)
        file.refresh_from_db()
        self.assertEqual(file.name, "guide.txt")

    def test_admin_can_manage_member_records_without_transferring_ownership(self):
        file = self.upload()
        folder = Folder.objects.create(owner=self.owner, name="Owner folder")
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("vault:list")), file.name)
        response = self.client.post(reverse("vault:edit", args=[file.pk]), {"name": "admin-renamed.txt", "folder": str(folder.pk)})
        self.assertEqual(response.status_code, 302)
        file.refresh_from_db()
        self.assertEqual((file.name, file.owner, file.folder), ("admin-renamed.txt", self.owner, folder))
        response = self.client.post(reverse("vault:folder_edit", args=[folder.pk]), {"name": "Renamed folder", "parent": ""})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Folder.objects.get(pk=folder.pk).owner, self.owner)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(reverse("vault:delete", args=[file.pk]), {"confirm": "yes"}).status_code, 302)
        self.assertEqual(self.client.post(reverse("vault:folder_delete", args=[folder.pk]), {"confirm": "yes"}).status_code, 302)

    def test_nested_folder_create_move_rename_and_delete(self):
        parent = Folder.objects.create(owner=self.owner, name="Guides")
        response = self.client.post(reverse("vault:folder_create"), {"name": "Nested", "parent": str(parent.pk)})
        child = Folder.objects.get(name="Nested")
        self.assertRedirects(response, reverse("vault:folder", args=[child.pk]))
        self.assertEqual((child.owner, child.parent), (self.owner, parent))
        self.assertContains(self.client.get(reverse("vault:folder", args=[child.pk])), "Up to Guides")
        self.assertEqual(self.client.post(reverse("vault:folder_edit", args=[child.pk]), {"name": "Reference", "parent": ""}).status_code, 302)
        child.refresh_from_db()
        self.assertEqual((child.name, child.parent), ("Reference", None))
        self.assertEqual(self.client.post(reverse("vault:folder_delete", args=[child.pk]), {"confirm": "yes"}).status_code, 302)
        self.assertFalse(Folder.objects.filter(pk=child.pk).exists())

    def test_cross_owner_destinations_and_forged_owner_are_rejected(self):
        other_folder = Folder.objects.create(owner=self.other, name="Other")
        file = self.upload()
        response = self.client.post(reverse("vault:edit", args=[file.pk]), {"name": "changed", "folder": str(other_folder.pk), "owner": self.other.pk})
        self.assertContains(response, "Select a valid choice")
        response = self.client.post(reverse("vault:folder_create"), {"name": "Forged", "parent": str(other_folder.pk), "owner": self.other.pk})
        self.assertContains(response, "Select a valid choice")
        file.refresh_from_db()
        self.assertEqual((file.name, file.owner), ("guide.txt", self.owner))
        self.assertFalse(Folder.objects.filter(name="Forged").exists())

    def test_duplicate_folder_and_cycles_show_validation_errors(self):
        parent = Folder.objects.create(owner=self.owner, name="Guides")
        child = Folder.objects.create(owner=self.owner, parent=parent, name="Child")
        response = self.client.post(reverse("vault:folder_create"), {"name": " guides ", "parent": ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Folder.objects.filter(owner=self.owner, parent=None).count(), 1)
        response = self.client.post(reverse("vault:folder_edit", args=[parent.pk]), {"name": "Guides", "parent": str(child.pk)})
        self.assertContains(response, "descendants")
        parent.refresh_from_db()
        self.assertIsNone(parent.parent)

    def test_subtree_move_cannot_exceed_depth_limit(self):
        parent = None
        for number in range(12):
            parent = Folder.objects.create(owner=self.owner, parent=parent, name=f"Depth {number}")
        root = Folder.objects.create(owner=self.owner, name="Move root")
        Folder.objects.create(owner=self.owner, parent=root, name="Move child")
        response = self.client.post(reverse("vault:folder_edit", args=[root.pk]), {"name": root.name, "parent": str(parent.pk)})
        self.assertContains(response, "maximum folder depth")
        root.refresh_from_db()
        self.assertIsNone(root.parent)

    def test_delete_requires_confirmation_and_empty_folder(self):
        folder = Folder.objects.create(owner=self.owner, name="Nonempty")
        file = self.upload(folder)
        response = self.client.post(reverse("vault:folder_delete", args=[folder.pk]), {"confirm": "yes"})
        self.assertContains(response, "Only empty folders")
        self.assertEqual(self.client.get(reverse("vault:delete", args=[file.pk])).status_code, 200)
        response = self.client.post(reverse("vault:delete", args=[file.pk]), {})
        self.assertContains(response, "Please confirm")
        self.assertTrue(VaultFile.objects.filter(pk=file.pk).exists())
        self.assertTrue(Folder.objects.filter(pk=folder.pk).exists())

    def test_blank_and_oversized_uploads_show_errors_without_creating_records(self):
        self.assertContains(self.client.post(reverse("vault:upload"), {}), "This field is required")
        self.assertContains(self.client.post(reverse("vault:folder_create"), {}), "This field is required")
        with override_settings(MAX_UPLOAD_BYTES=4):
            response = self.client.post(reverse("vault:upload"), {"file": SimpleUploadedFile("large.txt", b"12345")})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(VaultFile.objects.exists())

    def test_storage_failure_shows_clear_error_and_does_not_save_record(self):
        with patch("django.core.files.storage.FileSystemStorage._save", side_effect=OSError("offline")):
            response = self.client.post(reverse("vault:upload"), {"file": SimpleUploadedFile("failed.txt", b"contents")})
        self.assertContains(response, "The file could not be stored")
        self.assertFalse(VaultFile.objects.exists())

    def test_deletion_retries_when_storage_is_temporarily_unavailable(self):
        file = self.upload()
        key = file.blob.name
        with patch("vault.services.default_storage.delete", side_effect=OSError("offline")):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(reverse("vault:delete", args=[file.pk]), {"confirm": "yes"})
        self.assertEqual(response.status_code, 302)
        job = StorageDeletionJob.objects.get(storage_key=key)
        self.assertEqual(job.attempts, 1)
        self.assertFalse(VaultFile.objects.filter(pk=file.pk).exists())
        job.next_attempt_at = timezone.now()
        job.save()
        self.assertEqual(process_deletions(), (1, 0))
        self.assertFalse(file.blob.storage.exists(key))

    def test_dashboard_counts_follow_role(self):
        self.upload()
        response = self.client.get(reverse("accounts:member_dashboard"))
        self.assertEqual(response.context["vault_file_count"], 1)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("accounts:member_dashboard")).context["vault_file_count"], 0)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("accounts:admin_dashboard")).context["vault_file_count"], 1)

from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from .forms import UploadForm
from .models import validate_name
from .services import can_manage


class VaultValidationTests(SimpleTestCase):
    def test_file_and_folder_names_reject_paths_and_control_characters(self):
        for name in ("", " ", ".", "..", "folder/file.txt", "folder\\file.txt", "bad\nname", "bad\x7fname"):
            with self.subTest(name=name), self.assertRaises(ValidationError):
                validate_name(name)
        validate_name("team-notes.pdf")

    @override_settings(MAX_UPLOAD_BYTES=4)
    def test_upload_form_rejects_empty_and_oversized_files(self):
        user = SimpleNamespace(pk=12, role="member")
        for upload in (
            SimpleUploadedFile("empty.txt", b""),
            SimpleUploadedFile("large.txt", b"12345"),
        ):
            form = UploadForm(files={"file": upload}, user=user)
            self.assertFalse(form.is_valid())
            self.assertIn("file", form.errors)

    def test_upload_form_accepts_valid_file(self):
        user = SimpleNamespace(pk=12, role="member")
        form = UploadForm(
            files={"file": SimpleUploadedFile("notes.txt", b"hello")},
            user=user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_access_is_limited_to_owner_unless_admin(self):
        owner = SimpleNamespace(pk=1, role="member", is_authenticated=True, is_active=True)
        other = SimpleNamespace(pk=2, role="member", is_authenticated=True, is_active=True)
        admin = SimpleNamespace(pk=3, role="admin", is_authenticated=True, is_active=True)
        self.assertTrue(can_manage(owner, owner.pk))
        self.assertFalse(can_manage(other, owner.pk))
        self.assertTrue(can_manage(admin, owner.pk))

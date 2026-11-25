"""HTTP and database regressions for the PD3 hardening checklist."""
import uuid
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.html import escape

from accounts.models import User
from accounts.views import server_error
from . import views
from .models import Folder, VaultFile


class VaultRequestHardeningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="owner", email="owner@example.test")
        cls.other = User.objects.create_user(username="other", email="other@example.test")
        cls.folder = Folder.objects.create(owner=cls.owner, name="Private folder")
        cls.file = VaultFile.objects.create(
            owner=cls.owner, folder=cls.folder, name="private.txt",
            description="Private description", blob="objects/not-stored", size_bytes=10,
        )

    def setUp(self):
        self.client.force_login(self.owner)

    def mutation_urls(self):
        return [
            reverse("vault:upload"), reverse("vault:folder_create"),
            reverse("vault:edit", args=[self.file.pk]),
            reverse("vault:folder_edit", args=[self.folder.pk]),
            reverse("vault:delete", args=[self.file.pk]),
            reverse("vault:folder_delete", args=[self.folder.pk]),
        ]

    def test_views_require_login_when_called_directly(self):
        request = RequestFactory().get("/vault/")
        request.user = AnonymousUser()
        calls = [
            (views.file_list, {}), (views.upload, {}), (views.folder_create, {}),
            (views.folder_edit, {"pk": self.folder.pk}),
            (views.file_detail, {"pk": self.file.pk}),
            (views.file_edit, {"pk": self.file.pk}),
            (views.file_delete, {"pk": self.file.pk}),
            (views.folder_delete, {"pk": self.folder.pk}),
            (views.download, {"pk": self.file.pk}),
        ]
        for view, kwargs in calls:
            with self.subTest(view=view.__name__):
                self.assertEqual(view(request, **kwargs).status_code, 302)

    def test_invalid_workspace_role_is_denied_inside_view(self):
        from django.core.exceptions import PermissionDenied

        request = RequestFactory().get("/vault/")
        request.user = User(pk=self.owner.pk, role="unexpected")
        with self.assertRaises(PermissionDenied):
            views.file_list(request)

    def test_inactive_user_is_denied_inside_view(self):
        from django.core.exceptions import PermissionDenied

        request = RequestFactory().get("/vault/")
        request.user = User(pk=self.owner.pk, role=User.Role.MEMBER, is_active=False)
        with self.assertRaises(PermissionDenied):
            views.file_detail(request, self.file.pk)

    def test_authenticated_posts_without_csrf_are_blocked(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        for url in self.mutation_urls():
            with self.subTest(url=url):
                self.assertEqual(client.post(url, {"confirm": "yes"}).status_code, 403)
        self.assertTrue(VaultFile.objects.filter(pk=self.file.pk).exists())

    def test_every_core_mutation_form_contains_csrf_token(self):
        for url in self.mutation_urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'name="csrfmiddlewaretoken"')
                self.assertContains(response, 'method="post"')

    def test_get_requests_never_update_or_delete_records(self):
        for url in self.mutation_urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, {"name": "forged", "confirm": "yes"}).status_code, 200)
        self.file.refresh_from_db()
        self.folder.refresh_from_db()
        self.assertEqual(self.file.name, "private.txt")
        self.assertEqual(self.folder.name, "Private folder")
        self.assertEqual((VaultFile.objects.count(), Folder.objects.count()), (1, 1))

    def test_put_patch_and_delete_methods_cannot_mutate_records(self):
        for method in ("PUT", "PATCH", "DELETE"):
            for url in self.mutation_urls():
                with self.subTest(method=method, url=url):
                    self.assertEqual(self.client.generic(method, url).status_code, 405)
        self.assertTrue(VaultFile.objects.filter(pk=self.file.pk).exists())

    @override_settings(DEBUG=False)
    def test_malformed_and_missing_ids_use_custom_404_without_debug_details(self):
        for pk in ("not-a-uuid", str(uuid.uuid4())):
            for suffix in ("", "edit/", "delete/", "download/"):
                with self.subTest(pk=pk, suffix=suffix):
                    response = self.client.get(f"/vault/files/{pk}/{suffix}")
                    self.assertContains(response, "This page could not be found.", status_code=404)
                    self.assertNotContains(response, "Traceback", status_code=404)

    def test_invalid_destination_ids_show_safe_error_pages(self):
        for route, parameter in (("upload", "folder"), ("folder_create", "parent")):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse("vault:" + route), {parameter: "broken"}).status_code, 404)

    def test_other_member_cannot_post_changes_to_files_or_folders(self):
        self.client.force_login(self.other)
        for route, pk in (
            ("edit", self.file.pk), ("delete", self.file.pk),
            ("folder_edit", self.folder.pk), ("folder_delete", self.folder.pk),
        ):
            with self.subTest(route=route):
                response = self.client.post(reverse("vault:" + route, args=[pk]), {"name": "stolen", "confirm": "yes"})
                self.assertEqual(response.status_code, 404)
        self.file.refresh_from_db()
        self.assertEqual(self.file.name, "private.txt")

    def test_user_content_is_escaped_in_list_and_detail(self):
        name = '<img src=x onerror=alert(1)>.txt'
        description = '<script>alert("private")</script>'
        response = self.client.post(reverse("vault:edit", args=[self.file.pk]), {
            "name": name, "description": description, "folder": "",
        })
        self.assertEqual(response.status_code, 302)
        for route, args in (("list", []), ("detail", [self.file.pk])):
            response = self.client.get(reverse("vault:" + route, args=args))
            self.assertContains(response, escape(name))
            self.assertNotContains(response, name)
            self.assertNotContains(response, description)
        self.assertContains(response, escape(description))

    def test_missing_upload_bytes_return_404_instead_of_crashing(self):
        response = self.client.get(reverse("vault:download", args=[self.file.pk]))
        self.assertEqual(response.status_code, 404)

    @override_settings(DEBUG=False)
    def test_unexpected_failure_uses_custom_500_without_exception_message(self):
        client = Client(raise_request_exception=False)
        client.force_login(self.owner)
        with patch("vault.views.visible_files", side_effect=RuntimeError("DO_NOT_DISCLOSE")):
            with self.assertLogs("django.request", level="ERROR"):
                response = client.get(reverse("vault:list"))
        self.assertContains(response, "We could not complete that request.", status_code=500)
        self.assertNotContains(response, "DO_NOT_DISCLOSE", status_code=500)
        self.assertNotContains(response, "Traceback", status_code=500)

    def test_custom_500_handler_can_render_without_database_queries(self):
        with self.assertNumQueries(0):
            response = server_error(RequestFactory().get("/vault/"))
        self.assertEqual(response.status_code, 500)

    def test_list_query_count_does_not_grow_with_number_of_files(self):
        with CaptureQueriesContext(connection) as baseline:
            self.assertEqual(self.client.get(reverse("vault:list")).status_code, 200)
        for number in range(15):
            VaultFile.objects.create(owner=self.owner, name=f"file-{number}.txt", blob="objects/test", size_bytes=1)
        with CaptureQueriesContext(connection) as expanded:
            response = self.client.get(reverse("vault:list"))
            self.assertContains(response, "file-14.txt")
        self.assertLessEqual(len(expanded), len(baseline) + 1)


class VaultConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="owner", email="owner@example.test")

    def test_database_rejects_case_insensitive_root_folder_duplicates(self):
        Folder.objects.create(owner=self.owner, name="Guides")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Folder.objects.create(owner=self.owner, name="gUIDES")

    def test_database_rejects_case_insensitive_sibling_folder_duplicates(self):
        parent = Folder.objects.create(owner=self.owner, name="Parent")
        Folder.objects.create(owner=self.owner, name="Guides", parent=parent)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Folder.objects.create(owner=self.owner, name="guides", parent=parent)

    def test_database_rejects_folder_as_its_own_parent(self):
        folder = Folder.objects.create(owner=self.owner, name="Guides")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Folder.objects.filter(pk=folder.pk).update(parent_id=folder.pk)

    def test_database_rejects_zero_byte_file_metadata(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            VaultFile.objects.create(owner=self.owner, name="empty.txt", blob="objects/test", size_bytes=0)

    def test_database_rejects_invalid_user_role(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.filter(pk=self.owner.pk).update(role="unexpected")

    def test_folder_foreign_keys_protect_existing_contents(self):
        folder = Folder.objects.create(owner=self.owner, name="Parent")
        Folder.objects.create(owner=self.owner, name="Child", parent=folder)
        with self.assertRaises(ProtectedError):
            folder.delete()
        self.assertEqual(Folder.objects.count(), 2)

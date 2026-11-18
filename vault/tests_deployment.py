import uuid
from types import SimpleNamespace
from unittest.mock import patch

from botocore.exceptions import ClientError
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.db import OperationalError
from django.test import Client, RequestFactory, SimpleTestCase
from django.urls import reverse

from config.environment import database_config, private_storage_config, project_ref
from config.health import health
from .admin import VaultFileAdmin
from .models import VaultFile
from .storage import PrivateSupabaseStorage


class DeploymentChecks(SimpleTestCase):
    def test_local_storage_requires_debug(self):
        self.assertIn("FileSystemStorage", private_storage_config({}, debug=True)["BACKEND"])
        with self.assertRaises(ImproperlyConfigured):
            private_storage_config({"PRIVATE_STORAGE_BACKEND": "local"}, debug=False)
        with self.assertRaisesMessage(ImproperlyConfigured, "SUPABASE_S3"):
            private_storage_config({}, debug=False)

    def test_private_storage_configuration_requires_all_credentials(self):
        env = {"PRIVATE_STORAGE_BACKEND": "supabase", "SUPABASE_S3_ENDPOINT_URL": "https://test.storage.supabase.co/storage/v1/s3",
               "SUPABASE_S3_REGION": "ap-southeast-1", "SUPABASE_S3_ACCESS_KEY_ID": "test-key",
               "SUPABASE_S3_SECRET_ACCESS_KEY": "test-secret", "SUPABASE_STORAGE_BUCKET": "private-test"}
        options = private_storage_config(env, debug=False)["OPTIONS"]
        self.assertIsNone(options["default_acl"])
        self.assertIsNone(options["custom_domain"])
        for key in ("SUPABASE_S3_REGION", "SUPABASE_S3_ACCESS_KEY_ID", "SUPABASE_STORAGE_BUCKET"):
            with self.subTest(key=key), self.assertRaises(ImproperlyConfigured):
                private_storage_config({**env, key: ""}, debug=False)
        with self.assertRaises(ImproperlyConfigured):
            private_storage_config({**env, "SUPABASE_S3_ENDPOINT_URL": "http://untrusted.test/storage/v1/s3"}, debug=False)

    def test_storage_never_generates_a_public_or_signed_url(self):
        storage = PrivateSupabaseStorage(access_key="test", secret_key="test", bucket_name="test")
        with self.assertRaises(NotImplementedError):
            storage.url("objects/private-file")

    def test_s3_errors_are_translated_to_a_safe_storage_error(self):
        storage = PrivateSupabaseStorage(access_key="test", secret_key="test", bucket_name="test")
        error = ClientError({"Error": {"Code": "AccessDenied", "Message": "sensitive-provider-message"}}, "DeleteObject")
        with patch("storages.backends.s3.S3Storage.delete", side_effect=error):
            with self.assertRaisesMessage(OSError, "Private storage is unavailable"):
                storage.delete("objects/test")

    def test_health_reports_database_outages_without_details(self):
        request = RequestFactory().get("/health/")
        with patch("config.health.connection") as database:
            database.cursor.side_effect = OperationalError("secret-host")
            response = health(request)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"secret-host", response.content)
        with patch("config.health.connection"):
            self.assertEqual(health(request).status_code, 200)

    def test_local_postgresql_and_supabase_project_identity(self):
        self.assertEqual(database_config("postgresql://user:password@127.0.0.1:5432/app")["ENGINE"], "django.db.backends.postgresql")
        session = "postgresql://postgres.abc:password@aws-0-region.pooler.supabase.com:5432/postgres"
        direct = "postgresql://postgres:password@db.abc.supabase.co:5432/postgres"
        self.assertEqual(project_ref(session), project_ref(direct))

    def test_every_vault_endpoint_requires_login(self):
        pk = uuid.uuid4()
        routes = {"list": [], "upload": [], "folder_create": [], "folder": [pk], "folder_edit": [pk],
                  "folder_delete": [pk], "detail": [pk], "download": [pk], "edit": [pk], "delete": [pk]}
        for name, args in routes.items():
            url = reverse("vault:" + name, args=args)
            with self.subTest(route=name):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/accounts/login/?next=", response.url)
                self.assertIn("no-store", response["Cache-Control"])

    def test_vault_post_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        for name, args in (("upload", []), ("folder_create", []), ("edit", [uuid.uuid4()]), ("delete", [uuid.uuid4()])):
            self.assertEqual(client.post(reverse("vault:" + name, args=args), {}).status_code, 403)

    def test_maintenance_cannot_bypass_vault_mutations(self):
        from django.contrib import admin
        model_admin = VaultFileAdmin(VaultFile, admin.site)
        request = RequestFactory().get("/maintenance/")
        request.user = SimpleNamespace(role="admin", is_active=True, is_staff=True, is_superuser=True)
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))

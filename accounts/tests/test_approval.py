from io import StringIO
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from accounts.admin import WorkspaceUserAdmin
from accounts.forms import ProfileForm
from accounts.models import User
from accounts.services import change_account_access
from accounts import views
from vault.models import Folder, VaultFile

PASSWORD = "A-long-test-password!374"


class AccountApprovalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="approver", email="approver@example.test", password=PASSWORD,
            role=User.Role.ADMIN, account_status=User.AccountStatus.APPROVED,
        )
        cls.member = User.objects.create_user(
            username="member", email="member@example.test", password=PASSWORD,
            account_status=User.AccountStatus.APPROVED,
        )
        cls.pending = User.objects.create_user(username="pending", email="pending@example.test", password=PASSWORD)

    def setUp(self):
        self.client.force_login(self.admin)

    def url(self, account=None):
        return reverse("accounts:account_access", args=[(account or self.pending).pk])

    def payload(self, account=None, **overrides):
        account = account or self.pending
        account.refresh_from_db()
        data = {"role": account.role, "account_status": "APPROVED", "version": account.session_version, "confirm": "on"}
        return data | overrides

    def test_registration_always_creates_pending_member(self):
        self.client.logout()
        response = self.client.post(reverse("accounts:register"), {
            "username": "newuser", "email": "New@Example.test", "password1": PASSWORD, "password2": PASSWORD,
            "role": "admin", "account_status": "APPROVED", "is_active": "on", "is_staff": "on", "is_superuser": "on",
        })
        self.assertRedirects(response, reverse("accounts:registered"))
        user = User.objects.get(username="newuser")
        self.assertEqual((user.role, user.account_status, user.is_active), ("member", "PENDING", False))
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertContains(self.client.get(reverse("accounts:registered")), "Awaiting approval")

    def test_unapproved_accounts_cannot_authenticate_or_use_forced_sessions(self):
        for status in ("PENDING", "REJECTED", "INACTIVE"):
            with self.subTest(status=status):
                User.objects.filter(pk=self.pending.pk).update(account_status=status, is_active=False)
                self.assertIsNone(authenticate(username=self.pending.username, password=PASSWORD))
                client = Client()
                response = client.post(reverse("accounts:login"), {"username": "pending", "password": PASSWORD})
                self.assertContains(response, "must also be approved and active")
                self.assertNotIn("_auth_user_id", client.session)
                self.pending.refresh_from_db()
                client.force_login(self.pending)
                for url in (reverse("accounts:profile"), reverse("accounts:dashboard"), reverse("vault:list")):
                    response = client.get(url)
                    self.assertEqual(response.status_code, 302)
                    self.assertIn(reverse("accounts:login"), response.url)

    def test_approved_member_can_login_and_edit_own_profile(self):
        self.client.logout()
        response = self.client.post(reverse("accounts:login"), {"username": "member", "password": PASSWORD})
        self.assertRedirects(response, reverse("accounts:dashboard"), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("accounts:member_dashboard")).status_code, 200)
        response = self.client.post(reverse("accounts:profile"), {
            "first_name": "Member", "email": "changed@example.test", "role": "admin",
            "account_status": "REJECTED", "is_active": False,
        })
        self.assertRedirects(response, reverse("accounts:profile"))
        self.member.refresh_from_db()
        self.assertEqual((self.member.role, self.member.account_status, self.member.is_active), ("member", "APPROVED", True))

    def test_workspace_admin_without_staff_privileges_can_approve(self):
        self.assertFalse(self.admin.is_staff)
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertContains(response, reverse("accounts:account_list"))
        self.assertEqual(response.context["pending_count"], 1)
        self.assertContains(self.client.get(self.url()), 'name="csrfmiddlewaretoken"')
        response = self.client.post(self.url(), self.payload())
        self.assertRedirects(response, reverse("accounts:account_list"))
        self.pending.refresh_from_db()
        self.assertEqual((self.pending.account_status, self.pending.is_active), ("APPROVED", True))
        self.assertIsNotNone(authenticate(username="pending", password=PASSWORD))

    def test_reject_deactivate_and_reactivate_account(self):
        for status in ("REJECTED", "APPROVED", "INACTIVE", "APPROVED", "PENDING"):
            with self.subTest(status=status):
                response = self.client.post(self.url(), self.payload(account_status=status))
                self.assertRedirects(response, reverse("accounts:account_list"))
                self.pending.refresh_from_db()
                self.assertEqual(self.pending.account_status, status)
                self.assertEqual(self.pending.is_active, status == "APPROVED")
        self.assertEqual(self.pending.session_version, 5)

    def test_admin_can_assign_and_remove_workspace_admin_role(self):
        response = self.client.post(self.url(), self.payload(role="admin"))
        self.assertRedirects(response, reverse("accounts:account_list"))
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.role, "admin")
        client = Client()
        client.force_login(self.pending)
        self.assertEqual(client.get(reverse("accounts:account_list")).status_code, 200)
        self.client.post(self.url(), self.payload(role="member"))
        # The old Admin session is invalidated on demotion.
        self.assertEqual(client.get(reverse("accounts:account_list")).status_code, 302)
        self.pending.refresh_from_db()
        client.force_login(self.pending)
        self.assertEqual(client.get(reverse("accounts:account_list")).status_code, 403)

    def test_account_management_requires_login_and_admin_role(self):
        urls = (reverse("accounts:account_list"), self.url())
        self.client.logout()
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 302)
            self.assertEqual(self.client.post(url, self.payload()).status_code, 302)
        self.client.force_login(self.member)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, self.payload()).status_code, 403)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.account_status, "PENDING")

    def test_pending_admin_is_denied_inside_view_even_with_forged_active_flag(self):
        request = RequestFactory().get(reverse("accounts:account_list"))
        request.user = User(pk=self.pending.pk, role="admin", is_active=True, account_status="PENDING")
        with self.assertRaises(PermissionDenied):
            views.account_list(request)

    def test_access_changes_require_confirmation_and_csrf(self):
        data = self.payload()
        data.pop("confirm")
        self.assertContains(self.client.post(self.url(), data), "This field is required.")
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(self.url(), self.payload()).status_code, 403)
        page = client.get(self.url())
        self.assertContains(page, 'name="csrfmiddlewaretoken"')
        data = self.payload() | {"csrfmiddlewaretoken": client.cookies["csrftoken"].value}
        self.assertRedirects(client.post(self.url(), data), reverse("accounts:account_list"))

    def test_get_and_unsupported_methods_cannot_change_access(self):
        self.assertEqual(self.client.get(self.url(), self.payload()).status_code, 200)
        for method in ("put", "patch", "delete"):
            self.assertEqual(getattr(self.client, method)(self.url(), self.payload()).status_code, 405)
        self.pending.refresh_from_db()
        self.assertEqual((self.pending.account_status, self.pending.session_version), ("PENDING", 0))

    def test_invalid_role_status_and_version_are_rejected(self):
        for override in ({"role": "superuser"}, {"account_status": "ACTIVE"}, {"version": -1}, {"version": "invalid"}):
            with self.subTest(override=override):
                response = self.client.post(self.url(), self.payload(**override))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.account_status, "PENDING")

    def test_unknown_or_malformed_account_id_returns_404(self):
        for url in (reverse("accounts:account_access", args=[999999]), "/accounts/manage/not-an-id/", "/accounts/manage/999999999999999999999999999999/"):
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, self.payload()).status_code, 404)

    def test_admin_cannot_change_own_access_or_a_maintenance_account(self):
        operator = User.objects.create_superuser("operator", "operator@example.test", PASSWORD)
        for account in (self.admin, operator):
            with self.subTest(account=account.username):
                response = self.client.post(self.url(account), self.payload(account, role="member", account_status="INACTIVE"))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].non_field_errors())
                account.refresh_from_db()
                self.assertEqual((account.role, account.account_status, account.is_active), ("admin", "APPROVED", True))

    def test_duplicate_and_stale_forms_do_not_overwrite_later_decisions(self):
        data = self.payload()
        self.client.post(self.url(), data)
        response = self.client.post(self.url(), data | {"account_status": "REJECTED"})
        self.assertContains(response, "changed while you were reviewing")
        self.pending.refresh_from_db()
        self.assertEqual((self.pending.account_status, self.pending.session_version), ("APPROVED", 1))
        response = self.client.post(self.url(), self.payload())
        self.assertContains(response, "No access changes were selected")

    def test_management_only_changes_role_status_and_session_version(self):
        original_password = self.pending.password
        response = self.client.post(self.url(), self.payload(
            username="forged", email="forged@example.test", password="forged", is_staff="on", is_superuser="on", id=self.admin.pk,
        ))
        self.assertEqual(response.status_code, 302)
        self.pending.refresh_from_db()
        self.assertEqual((self.pending.username, self.pending.email, self.pending.password), ("pending", "pending@example.test", original_password))
        self.assertFalse(self.pending.is_staff or self.pending.is_superuser)

    def test_rendered_account_data_is_escaped(self):
        User.objects.filter(pk=self.pending.pk).update(username='<script>alert("x")</script>')
        response = self.client.get(reverse("accounts:account_list"))
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, '<script>alert("x")</script>')

    def test_deactivation_preserves_files_and_old_cookie_stays_revoked_after_reactivation(self):
        folder = Folder.objects.create(owner=self.member, name="Retained")
        file = VaultFile.objects.create(owner=self.member, folder=folder, name="retained.txt", blob="objects/retained", size_bytes=1)
        active_client, stale_client = Client(), Client()
        active_client.force_login(self.member)
        stale_client.cookies = active_client.cookies.copy()
        self.client.post(self.url(self.member), self.payload(self.member, account_status="INACTIVE"))
        self.assertEqual(active_client.get(reverse("vault:list")).status_code, 302)
        self.client.post(self.url(self.member), self.payload(self.member))
        self.assertEqual(stale_client.get(reverse("vault:list")).status_code, 302)
        self.assertTrue(Folder.objects.filter(pk=folder.pk, owner=self.member).exists())
        self.assertTrue(VaultFile.objects.filter(pk=file.pk, owner=self.member).exists())

    def test_service_rechecks_admin_permissions_and_session_version(self):
        User.objects.filter(pk=self.admin.pk).update(role="member", session_version=1)
        with self.assertRaises(PermissionDenied):
            change_account_access(self.admin, self.pending.pk, role="member", account_status="APPROVED", version=0)
        User.objects.filter(pk=self.admin.pk).update(role="admin")
        with self.assertRaises(PermissionDenied):
            change_account_access(self.admin, self.pending.pk, role="member", account_status="APPROVED", version=0)

    def test_profile_save_cannot_undo_an_admin_deactivation(self):
        self.client.force_login(self.member)
        original_save = ProfileForm.save

        def deactivate_before_save(form, commit=True):
            User.objects.filter(pk=self.member.pk).update(account_status="INACTIVE", is_active=False, session_version=1)
            return original_save(form, commit=commit)

        with patch.object(ProfileForm, "save", autospec=True, side_effect=deactivate_before_save):
            self.assertEqual(self.client.post(reverse("accounts:profile"), {"email": "new@example.test"}).status_code, 302)
        self.member.refresh_from_db()
        self.assertEqual((self.member.account_status, self.member.is_active, self.member.session_version), ("INACTIVE", False, 1))

    def test_account_list_paginates_and_handles_invalid_page(self):
        User.objects.bulk_create([User(username=f"extra{n}", email=f"extra{n}@example.test") for n in range(26)])
        response = self.client.get(reverse("accounts:account_list"))
        self.assertEqual(len(response.context["page_obj"]), 25)
        for page in ("invalid", "999999", "-1"):
            self.assertEqual(self.client.get(reverse("accounts:account_list"), {"page": page}).status_code, 200)

    def test_database_rejects_invalid_or_inconsistent_status(self):
        for values in ({"account_status": "unknown"}, {"is_active": True}, {"account_status": "APPROVED"}):
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                User.objects.filter(pk=self.pending.pk).update(**values)

    def test_bootstrap_command_approves_admin_without_staff_privileges(self):
        call_command("promote_workspace_admin", "pending", stdout=StringIO())
        self.pending.refresh_from_db()
        self.assertEqual((self.pending.role, self.pending.account_status, self.pending.is_active, self.pending.session_version), ("admin", "APPROVED", True, 1))
        self.assertFalse(self.pending.is_staff or self.pending.is_superuser)

    def test_superuser_is_approved_admin_and_maintenance_is_read_only(self):
        operator = User.objects.create_superuser("operator", "operator@example.test", PASSWORD)
        self.assertEqual((operator.role, operator.account_status, operator.is_active), ("admin", "APPROVED", True))
        self.assertIsNotNone(authenticate(username="operator", password=PASSWORD))
        request = RequestFactory().get("/maintenance/")
        request.user = operator
        model_admin = WorkspaceUserAdmin(User, admin.site)
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request, self.member))
        self.assertFalse(model_admin.has_delete_permission(request, self.member))

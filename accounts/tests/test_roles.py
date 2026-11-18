from unittest.mock import patch
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, SimpleTestCase
from accounts import views
from accounts.forms import RegistrationForm
from accounts.models import User


class RoleChecks(SimpleTestCase):
    def request_for(self, role):
        request = RequestFactory().get("/accounts/dashboard/")
        request.user = User(username="crew", email="crew@example.test", role=role)
        return request

    def test_router_selects_users_role(self):
        for role in User.Role.values:
            self.assertEqual(views.dashboard(self.request_for(role)).url, f"/accounts/dashboard/{role}/")

    def test_member_cannot_open_admin_dashboard(self):
        with self.assertRaises(PermissionDenied):
            views.admin_dashboard(self.request_for(User.Role.MEMBER))

    def test_admin_cannot_open_member_dashboard(self):
        with self.assertRaises(PermissionDenied):
            views.member_dashboard(self.request_for(User.Role.ADMIN))

    def test_visitors_cannot_open_either_dashboard(self):
        for path in ("member", "admin"):
            response = self.client.get(f"/accounts/dashboard/{path}/")
            self.assertEqual(response.status_code, 302)
            self.assertIn("/accounts/login/?next=", response.url)

    def test_registration_does_not_expose_privileges(self):
        form = RegistrationForm({"role": "admin", "is_staff": True})
        self.assertNotIn("role", form.fields)
        self.assertNotIn("is_staff", form.fields)
        self.assertEqual(form.instance.role, User.Role.MEMBER)

    def test_member_dashboard_contains_member_content(self):
        with patch("vault.models.VaultFile.objects.filter") as files:
            files.return_value.count.return_value = 0
            response = views.member_dashboard(self.request_for(User.Role.MEMBER))
        self.assertContains(response, "Member workspace")
        self.assertNotContains(response, "Recently joined")

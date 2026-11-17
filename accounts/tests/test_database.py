import os
from unittest import skipUnless
from django.test import TestCase
from accounts.models import User

PASSWORD = "A-long-test-password!374"


@skipUnless(os.getenv("TEST_DATABASE_URL"), "Requires a separate disposable Supabase TEST_DATABASE_URL")
class RegistrationJourney(TestCase):
    def test_registration_persists_and_rejects_duplicate_email(self):
        data = {"username": "alice", "email": "Alice@Example.test", "password1": PASSWORD, "password2": PASSWORD}
        response = self.client.post("/accounts/register/", data)
        self.assertRedirects(response, "/accounts/registered/")
        user = User.objects.get(username="alice")
        self.assertTrue(user.check_password(PASSWORD))
        data.update(username="bob", email="ALICE@example.test")
        response = self.client.post("/accounts/register/", data)
        self.assertContains(response, "This email address is already in use.")
        self.assertEqual(User.objects.count(), 1)

    def test_login_logout_and_session_protection(self):
        User.objects.create_user(username="alice", email="alice@example.test", password=PASSWORD)
        response = self.client.post("/accounts/login/", {"username": "alice", "password": PASSWORD})
        self.assertRedirects(response, "/accounts/dashboard/", fetch_redirect_response=False)
        self.assertContains(self.client.get("/accounts/dashboard/member/"), "Hello, alice")
        self.assertRedirects(self.client.post("/accounts/logout/"), "/accounts/login/")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertRedirects(self.client.get("/accounts/dashboard/"), "/accounts/login/?next=/accounts/dashboard/", fetch_redirect_response=False)

    def test_roles_are_enforced_at_direct_urls(self):
        member = User.objects.create_user(username="member", email="member@example.test", password=PASSWORD)
        admin = User.objects.create_user(username="admin", email="admin@example.test", password=PASSWORD, role=User.Role.ADMIN)
        self.client.force_login(member)
        self.assertEqual(self.client.get("/accounts/dashboard/admin/").status_code, 403)
        self.assertRedirects(self.client.get("/accounts/dashboard/"), "/accounts/dashboard/member/")
        self.client.force_login(admin)
        self.assertEqual(self.client.get("/accounts/dashboard/member/").status_code, 403)
        response = self.client.get("/accounts/dashboard/admin/")
        self.assertEqual(response.context["counts"], {"total": 2, "members": 1, "admins": 1})

    def test_profile_changes_persist_without_privilege_escalation(self):
        user = User.objects.create_user(username="alice", email="alice@example.test", password=PASSWORD)
        other = User.objects.create_user(username="bob", email="bob@example.test", password=PASSWORD)
        self.client.force_login(user)
        response = self.client.post("/accounts/profile/?user_id=" + str(other.pk), {
            "first_name": "Alice", "last_name": "Crew", "email": "NEW@Example.test",
            "role": "admin", "is_staff": "on", "username": "bob", "id": other.pk,
        })
        self.assertRedirects(response, "/accounts/profile/")
        user.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual((user.first_name, user.last_name, user.email), ("Alice", "Crew", "new@example.test"))
        self.assertEqual(user.role, User.Role.MEMBER)
        self.assertFalse(user.is_staff)
        self.assertEqual(user.username, "alice")
        self.assertEqual(other.email, "bob@example.test")
        self.assertEqual(self.client.get(f"/accounts/profile/{other.pk}/").status_code, 404)

    def test_duplicate_profile_email_does_not_change_account(self):
        user = User.objects.create_user(username="alice", email="alice@example.test", password=PASSWORD)
        User.objects.create_user(username="bob", email="bob@example.test", password=PASSWORD)
        self.client.force_login(user)
        response = self.client.post("/accounts/profile/", {"email": "BOB@example.test"})
        self.assertContains(response, "This email address is already in use.")
        user.refresh_from_db()
        self.assertEqual(user.email, "alice@example.test")

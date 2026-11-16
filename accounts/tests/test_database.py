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
        self.assertRedirects(response, "/accounts/dashboard/")
        self.assertContains(self.client.get("/accounts/dashboard/"), "Welcome, alice")
        self.assertRedirects(self.client.post("/accounts/logout/"), "/accounts/login/")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertRedirects(self.client.get("/accounts/dashboard/"), "/accounts/login/?next=/accounts/dashboard/", fetch_redirect_response=False)

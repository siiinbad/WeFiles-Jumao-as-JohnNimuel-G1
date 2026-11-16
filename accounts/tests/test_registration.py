from unittest.mock import patch
from django.test import SimpleTestCase
from accounts.forms import RegistrationForm
from accounts.models import User
from config.environment import database_config


class RegistrationChecks(SimpleTestCase):
    def test_registration_requires_email_and_matching_passwords(self):
        form = RegistrationForm({"username": "", "email": "bad", "password1": "Abc", "password2": "Different"})
        with patch.object(User, "validate_unique"), patch.object(User, "validate_constraints"):
            self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn("username", form.errors)
        self.assertIn("password2", form.errors)

    def test_password_is_hashed(self):
        user = User(username="member", email="member@example.test")
        user.set_password("A-long-test-password!374")
        self.assertNotEqual(user.password, "A-long-test-password!374")
        self.assertTrue(user.check_password("A-long-test-password!374"))

    def test_case_insensitive_username_validation(self):
        form = RegistrationForm()
        form.cleaned_data = {"username": "Alice"}
        with patch.object(User.objects, "filter") as query:
            query.return_value.exists.return_value = True
            with self.assertRaisesMessage(Exception, "already in use"):
                form.clean_username()
            query.assert_called_once_with(username__iexact="Alice")

    def test_transaction_pooler_disables_connection_reuse(self):
        config = database_config("postgresql://postgres.test:placeholder@aws-0-region.pooler.supabase.com:6543/postgres")
        self.assertEqual(config["CONN_MAX_AGE"], 0)
        self.assertTrue(config["DISABLE_SERVER_SIDE_CURSORS"])
        self.assertEqual(config["OPTIONS"]["sslmode"], "require")

    def test_sqlite_is_rejected(self):
        with self.assertRaisesMessage(Exception, "Supabase PostgreSQL"):
            database_config("sqlite:///db.sqlite3")

    def test_registration_page_and_csrf(self):
        self.assertContains(self.client.get("/accounts/register/"), "csrfmiddlewaretoken")
        self.assertEqual(self.client.get("/accounts/register/")["Cache-Control"], "private, no-store")

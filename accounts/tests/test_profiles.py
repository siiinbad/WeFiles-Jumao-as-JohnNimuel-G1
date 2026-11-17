from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.test import Client, RequestFactory, SimpleTestCase
from accounts.forms import ProfileForm
from accounts.models import User
from accounts import views


class ProfileChecks(SimpleTestCase):
    def test_profile_requires_login(self):
        response = self.client.get("/accounts/profile/")
        self.assertRedirects(response, "/accounts/login/?next=/accounts/profile/", fetch_redirect_response=False)

    def test_profile_requires_csrf(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post("/accounts/profile/", {}).status_code, 403)

    def test_profile_uses_session_user_even_if_another_id_is_requested(self):
        user = User(pk=7, username="mine", email="mine@example.test")
        request = RequestFactory().get("/accounts/profile/", {"user_id": 99})
        request.user = user
        with patch.object(views, "render") as render:
            views.profile(request)
        self.assertIs(render.call_args.args[2]["form"].instance, user)

    def test_profile_excludes_identity_and_privileges(self):
        form = ProfileForm({"role": "admin", "is_staff": True, "username": "somebody_else"})
        self.assertEqual(set(form.fields), {"first_name", "last_name", "email"})

    def test_email_normalizes_and_excludes_current_account(self):
        user = User(pk=7, username="mine", email="mine@example.test")
        form = ProfileForm(instance=user)
        form.cleaned_data = {"email": " MY.NEW@Example.test "}
        with patch.object(User.objects, "filter") as query:
            query.return_value.exclude.return_value.exists.return_value = False
            self.assertEqual(form.clean_email(), "my.new@example.test")
            query.return_value.exclude.assert_called_once_with(pk=7)

    def test_duplicate_email_is_rejected(self):
        form = ProfileForm(instance=User(pk=7))
        form.cleaned_data = {"email": "taken@example.test"}
        with patch.object(User.objects, "filter") as query:
            query.return_value.exclude.return_value.exists.return_value = True
            with self.assertRaisesMessage(ValidationError, "already in use"):
                form.clean_email()

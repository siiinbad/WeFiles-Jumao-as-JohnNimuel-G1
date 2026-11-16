from unittest.mock import patch
from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory, SimpleTestCase
from accounts import views
from accounts.models import User


class SessionChecks(SimpleTestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get("/accounts/dashboard/")
        self.assertRedirects(response, "/accounts/login/?next=/accounts/dashboard/", fetch_redirect_response=False)

    def test_post_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        for path in ("/accounts/register/", "/accounts/login/", "/accounts/logout/"):
            self.assertEqual(client.post(path, {}).status_code, 403)

    def test_logout_rejects_get(self):
        self.assertEqual(self.client.get("/accounts/logout/").status_code, 405)

    def test_invalid_credentials_show_error(self):
        with patch("django.contrib.auth.forms.authenticate", return_value=None):
            response = self.client.post("/accounts/login/", {"username": "alice", "password": "wrong"})
        self.assertContains(response, "Please enter a correct username and password.")

    def test_login_rejects_external_redirect(self):
        request = RequestFactory().post("/accounts/login/", {"next": "https://attacker.example/"})
        request.user = AnonymousUser()
        user = User(username="alice", email="alice@example.test")
        with patch.object(views, "AuthenticationForm") as form, patch.object(views, "auth_login") as sign_in, patch.object(views.messages, "success"):
            form.return_value.is_valid.return_value = True
            form.return_value.get_user.return_value = user
            response = views.login(request)
        sign_in.assert_called_once_with(request, user)
        self.assertEqual(response.url, "/accounts/dashboard/")

"""Offline checks need no credentials; database tests use a disposable PostgreSQL DB."""
import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# Do not require production credentials for database-independent tests.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
application_database_url = os.getenv("DATABASE_URL", "")
os.environ["SECRET_KEY"] = "offline-tests-only-" + "x" * 64
os.environ["DJANGO_DEBUG"] = "True"
os.environ["PRIVATE_STORAGE_BACKEND"] = "local"
os.environ["DATABASE_URL"] = "postgresql://offline:offline@127.0.0.1:5432/wefiles_offline"
from .settings import *  # noqa: F403,E402
from .environment import database_config, project_ref  # noqa: E402

DEBUG = True
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
TEST_RUNNER = "accounts.tests.runner.ExistingDatabaseRunner"
if test_url := os.getenv("TEST_DATABASE_URL"):
    if project_ref(test_url) == project_ref(application_database_url):
        raise ImproperlyConfigured("TEST_DATABASE_URL must use a different database/project.")
    db = database_config(test_url)
    if ".supabase." in db["HOST"]:
        if os.getenv("ALLOW_DISPOSABLE_SUPABASE_TESTS") != "yes":
            raise ImproperlyConfigured("Set ALLOW_DISPOSABLE_SUPABASE_TESTS=yes only for an empty disposable TEST project; tests flush its tables.")
        db["TEST"] = {"NAME": db["NAME"]}
    DATABASES = {"default": db}

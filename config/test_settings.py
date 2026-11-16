"""Opt-in database tests use an existing, separate Supabase TEST project."""
import os
from django.core.exceptions import ImproperlyConfigured
from .settings import *  # noqa: F403
from .environment import database_config, project_ref

DEBUG = True
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
STORAGES = {"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
TEST_RUNNER = "accounts.tests.runner.ExistingDatabaseRunner"
if test_url := os.getenv("TEST_DATABASE_URL"):
    if project_ref(test_url) == project_ref(os.getenv("DATABASE_URL", "")):
        raise ImproperlyConfigured("TEST_DATABASE_URL must use a different Supabase project.")
    db = database_config(test_url)
    db["TEST"] = {"NAME": db["NAME"]}
    DATABASES = {"default": db}

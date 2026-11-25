import os
from django.core.exceptions import ImproperlyConfigured
from django.test.runner import DiscoverRunner
from django.conf import settings


class ExistingDatabaseRunner(DiscoverRunner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if ".supabase." in os.getenv("TEST_DATABASE_URL", "") and (not self.keepdb or self.parallel != 1):
            raise ValueError("Use --keepdb --parallel 1 with the disposable Supabase test project.")

    def get_databases(self, suite):
        databases = super().get_databases(suite)
        if databases and not os.getenv("TEST_DATABASE_URL"):
            database = settings.DATABASES["default"]
            if database["HOST"] not in {"localhost", "127.0.0.1", "::1"} or database["NAME"] == "wefiles_offline":
                raise ImproperlyConfigured(
                    "Configure a local DATABASE_URL whose login has CREATEDB, or a separate "
                    "disposable TEST_DATABASE_URL. Django creates a test_ database locally."
                )
        return databases

import os
from django.core.exceptions import ImproperlyConfigured
from django.test.runner import DiscoverRunner


class ExistingDatabaseRunner(DiscoverRunner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if os.getenv("TEST_DATABASE_URL") and (not self.keepdb or self.parallel != 1):
            raise ValueError("Use --keepdb --parallel 1 with the disposable Supabase test project.")

    def get_databases(self, suite):
        databases = super().get_databases(suite)
        if databases and not os.getenv("TEST_DATABASE_URL"):
            raise ImproperlyConfigured("Database tests require a separate TEST_DATABASE_URL.")
        return databases

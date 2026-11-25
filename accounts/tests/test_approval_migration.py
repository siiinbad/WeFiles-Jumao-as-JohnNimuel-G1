from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ExistingAccountMigrationTests(TransactionTestCase):
    old = [("accounts", "0002_user_role_user_accounts_role_valid")]
    new = [("accounts", "0003_account_approval")]

    def restore_schema(self):
        MigrationExecutor(connection).migrate(self.new)

    def test_existing_active_and_inactive_users_keep_access_state(self):
        self.addCleanup(self.restore_schema)
        executor = MigrationExecutor(connection)
        executor.migrate(self.old)
        old_user = executor.loader.project_state(self.old).apps.get_model("accounts", "User")
        old_user.objects.create(username="existing_admin", email="existing@example.test", role="admin", is_active=True)
        old_user.objects.create(username="disabled", email="disabled@example.test", is_active=False)
        executor = MigrationExecutor(connection)
        executor.migrate(self.new)
        user = executor.loader.project_state(self.new).apps.get_model("accounts", "User")
        existing, disabled = user.objects.get(username="existing_admin"), user.objects.get(username="disabled")
        self.assertEqual((existing.role, existing.account_status, existing.is_active), ("admin", "APPROVED", True))
        self.assertEqual((disabled.account_status, disabled.is_active), ("INACTIVE", False))
        new = user.objects.create(username="fresh", email="fresh@example.test")
        self.assertEqual((new.account_status, new.is_active), ("PENDING", False))

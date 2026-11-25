from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.core.exceptions import PermissionDenied
from django.db import close_old_connections, connections
from django.test import TransactionTestCase

from accounts.models import User
from accounts.services import change_account_access


class CompetingAdminChangesTests(TransactionTestCase):
    def test_admins_cannot_concurrently_deactivate_each_other(self):
        first, second = [User.objects.create_user(
            username=name, email=f"{name}@example.test", role="admin", account_status="APPROVED",
        ) for name in ("first_admin", "second_admin")]
        barrier = Barrier(2)

        def deactivate(actor, target):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    change_account_access(actor, target.pk, role="admin", account_status="INACTIVE", version=0)
                except PermissionDenied:
                    return "denied"
                return "updated"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(deactivate, first, second), executor.submit(deactivate, second, first)]
            results = [future.result(timeout=15) for future in futures]
        self.assertCountEqual(results, ["updated", "denied"])
        self.assertEqual(User.objects.filter(role="admin", account_status="APPROVED", is_active=True).count(), 1)

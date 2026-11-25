from django.contrib.auth.models import UserManager


class WorkspaceUserManager(UserManager):
    def _create_user_object(self, username, email, password, **extra_fields):
        status = extra_fields.setdefault("account_status", "PENDING")
        active = extra_fields.setdefault("is_active", status == "APPROVED")
        if status not in {"PENDING", "APPROVED", "REJECTED", "INACTIVE"}:
            raise ValueError("Unknown account status.")
        if active != (status == "APPROVED"):
            raise ValueError("Only approved accounts can be active.")
        return super()._create_user_object(username, email, password, **extra_fields)

    def _superuser_defaults(self, extra_fields):
        for field, value in (("role", "admin"), ("account_status", "APPROVED"), ("is_active", True)):
            if extra_fields.setdefault(field, value) != value:
                raise ValueError("A superuser must be an approved, active workspace Admin.")

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        self._superuser_defaults(extra_fields)
        return super().create_superuser(username, email, password, **extra_fields)

    create_superuser.alters_data = True

    async def acreate_superuser(self, username, email=None, password=None, **extra_fields):
        self._superuser_defaults(extra_fields)
        return await super().acreate_superuser(username, email, password, **extra_fields)

    acreate_superuser.alters_data = True

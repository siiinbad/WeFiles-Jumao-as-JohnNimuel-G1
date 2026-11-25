from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.utils.crypto import salted_hmac

from .managers import WorkspaceUserManager


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    class AccountStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        INACTIVE = "INACTIVE", "Inactive"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    account_status = models.CharField(max_length=10, choices=AccountStatus.choices, default=AccountStatus.PENDING)
    is_active = models.BooleanField(default=False, help_text="Only approved accounts may be active.")
    session_version = models.PositiveIntegerField(default=0, editable=False)

    objects = WorkspaceUserManager()

    def _get_session_auth_hash(self, secret=None):
        # Extend Django's session HMAC so restoring a role/status never revives
        # a cookie issued before an administrator revoked access.
        return salted_hmac(
            "accounts.User.get_session_auth_hash",
            f"{self.password}:{self.session_version}",
            secret=secret,
            algorithm="sha256",
        ).hexdigest()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(role__in=["admin", "member"]), name="accounts_role_valid"),
            models.CheckConstraint(
                condition=models.Q(account_status__in=["PENDING", "APPROVED", "REJECTED", "INACTIVE"]),
                name="accounts_status_valid",
            ),
            models.CheckConstraint(
                condition=(models.Q(account_status="APPROVED", is_active=True) |
                           (~models.Q(account_status="APPROVED") & models.Q(is_active=False))),
                name="accounts_status_matches_active",
            ),
            models.UniqueConstraint(Lower("username"), name="accounts_username_ci_unique"),
            models.UniqueConstraint(Lower("email"), name="accounts_email_ci_unique"),
        ]

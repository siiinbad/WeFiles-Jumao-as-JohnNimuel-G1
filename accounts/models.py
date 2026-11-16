from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(role__in=["admin", "member"]), name="accounts_role_valid"),
            models.UniqueConstraint(Lower("username"), name="accounts_username_ci_unique"),
            models.UniqueConstraint(Lower("email"), name="accounts_email_ci_unique"),
        ]

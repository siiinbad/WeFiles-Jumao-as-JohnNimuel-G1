from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import User


@transaction.atomic
def change_account_access(actor, account_id, *, role, account_status, version):
    # Lock current Admins in a stable order before any target. This serializes
    # competing changes (including two Admins trying to disable each other).
    admins = list(User.objects.select_for_update().filter(
        role=User.Role.ADMIN, account_status=User.AccountStatus.APPROVED, is_active=True,
    ).order_by("pk"))
    current_actor = next((admin for admin in admins if admin.pk == actor.pk), None)
    if (current_actor is None or not actor.is_authenticated or
            current_actor.session_version != actor.session_version):
        raise PermissionDenied
    account = get_object_or_404(User.objects.select_for_update(), pk=account_id)
    if account.pk == current_actor.pk:
        raise ValidationError("You cannot change your own role or status. Ask another workspace Admin.")
    if account.is_staff or account.is_superuser:
        raise ValidationError("This is a maintenance account. Its access is managed by the system operator.")
    if role not in User.Role.values or account_status not in User.AccountStatus.values:
        raise ValidationError("Choose a valid role and account status.")
    if account.session_version != version:
        raise ValidationError("This account changed while you were reviewing it. Reload the page and review again.")
    if (account.role, account.account_status) == (role, account_status):
        raise ValidationError("No access changes were selected.")
    account.role = role
    account.account_status = account_status
    account.is_active = account_status == User.AccountStatus.APPROVED
    account.session_version += 1
    account.save(update_fields=["role", "account_status", "is_active", "session_version"])
    return account

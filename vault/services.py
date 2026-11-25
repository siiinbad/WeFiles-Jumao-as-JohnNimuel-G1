"""Owner-scoped mutations and retryable deletion of private file objects."""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from .models import Folder, StorageDeletionJob, VaultFile, validate_name

logger = logging.getLogger(__name__)


def can_manage(user, owner_id):
    return bool(user.is_authenticated and user.is_active and
                user.account_status == User.AccountStatus.APPROVED and
                (user.role == User.Role.ADMIN or
                 (user.role == User.Role.MEMBER and user.pk == owner_id)))


def require_manage(user, owner_id):
    if not can_manage(user, owner_id):
        raise PermissionDenied


def lock_owner(user, owner_id):
    require_manage(user, owner_id)
    # One stable row serializes folder moves, uploads and deletions for this owner.
    if User.objects.select_for_update().filter(pk=owner_id).first() is None:
        raise ValidationError("This account is no longer available. Please sign in again.")


def locked_record(user, model, pk):
    """Recheck existence after the owner lock so stale requests cannot resurrect rows."""
    owner_id = model.objects.filter(pk=pk).values_list("owner_id", flat=True).first()
    if owner_id is None:
        raise ValidationError("This item was already deleted. Return to the vault and try again.")
    lock_owner(user, owner_id)
    item = model.objects.select_for_update().filter(pk=pk).first()
    if item is None:
        raise ValidationError("This item was already deleted. Return to the vault and try again.")
    require_manage(user, item.owner_id)
    return item


def destination(owner_id, folder_id):
    if not folder_id:
        return None
    folder = Folder.objects.filter(pk=folder_id, owner_id=owner_id).first()
    if folder is None:
        raise ValidationError("That destination is unavailable. Choose one of the owner's folders.")
    return folder


def upload_file(user, upload, folder=None, description=""):
    require_manage(user, user.pk)
    validate_name(upload.name)
    if not 0 < upload.size <= settings.MAX_UPLOAD_BYTES:
        raise ValidationError("The file is empty or exceeds the upload limit.")
    file = VaultFile(owner=user, name=upload.name, description=description,
                     size_bytes=upload.size, content_type=(upload.content_type or "")[:150])
    try:
        with transaction.atomic():
            lock_owner(user, user.pk)
            file.folder = destination(user.pk, folder.pk if folder else None)
            file.full_clean(exclude=["blob"])
            file.blob.save(upload.name, upload, save=False)
            file.full_clean()
            file.save()
    except Exception:
        if file.blob.name:
            try:
                file.blob.storage.delete(file.blob.name)
            except Exception:
                StorageDeletionJob.objects.get_or_create(storage_key=file.blob.name)
                logger.warning("Upload cleanup queued for retry")
        raise
    return file


@transaction.atomic
def save_folder(user, folder):
    if folder._state.adding:
        folder.owner = user
        lock_owner(user, folder.owner_id)
    else:
        saved = locked_record(user, Folder, folder.pk)
        saved.name, saved.parent_id = folder.name, folder.parent_id
        folder = saved
    folder.parent = destination(folder.owner_id, folder.parent_id)
    folder.full_clean()
    # Validate the height of the entire moved subtree, not just the moved folder.
    depth, parent = 0, folder.parent
    while parent:
        depth += 1
        parent = parent.parent
    children = {}
    for pk, parent_id in Folder.objects.filter(owner_id=folder.owner_id).values_list("pk", "parent_id"):
        children.setdefault(parent_id, []).append(pk)
    frontier, seen, height = [folder.pk], {folder.pk}, 0
    while frontier:
        frontier = [pk for parent_id in frontier for pk in children.get(parent_id, [])]
        if not frontier:
            break
        if any(pk in seen for pk in frontier):
            raise ValidationError("A folder cannot be moved inside its descendants.")
        seen.update(frontier)
        height += 1
    if depth + height > 12:
        raise ValidationError("This move would exceed the maximum folder depth of 12.")
    folder.save()
    return folder


@transaction.atomic
def update_file(user, file):
    saved = locked_record(user, VaultFile, file.pk)
    saved.name, saved.description = file.name, file.description
    saved.folder = destination(saved.owner_id, file.folder_id)
    saved.full_clean()
    saved.save(update_fields=["name", "description", "folder", "updated_at"])
    return saved


@transaction.atomic
def delete_folder(user, folder):
    folder = locked_record(user, Folder, folder.pk)
    if folder.children.exists() or folder.files.exists():
        raise ValidationError("Move or delete its contents first. Only empty folders can be deleted.")
    folder.delete()


def cleanup_after_commit():
    try:
        process_deletions(limit=10)
    except Exception:
        # Metadata deletion succeeded; the durable job remains for the next retry.
        logger.warning("Storage cleanup postponed; run process_storage_deletions")


@transaction.atomic
def delete_file(user, file):
    file = locked_record(user, VaultFile, file.pk)
    # The post_delete signal queues cleanup in this same transaction, including
    # deletions caused by Django's account cascade or maintenance commands.
    file.delete()


def process_deletions(limit=100):
    done = failed = 0
    ids = list(StorageDeletionJob.objects.filter(next_attempt_at__lte=timezone.now())
               .order_by("pk").values_list("pk", flat=True)[:limit])
    for job_id in ids:
        with transaction.atomic():
            job = StorageDeletionJob.objects.select_for_update().filter(pk=job_id).first()
            if not job or job.next_attempt_at > timezone.now():
                continue
            try:
                default_storage.delete(job.storage_key)
            except Exception as exc:
                job.attempts += 1
                job.last_error_code = type(exc).__name__[:80]
                job.next_attempt_at = timezone.now() + timedelta(
                    seconds=min(3600, 30 * 2 ** min(job.attempts, 7)))
                job.save()
                logger.warning("Private file deletion will be retried (%s)", job.last_error_code)
                failed += 1
            else:
                job.delete()
                done += 1
    return done, failed

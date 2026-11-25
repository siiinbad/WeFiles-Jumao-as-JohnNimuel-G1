"""Preserve private-object cleanup for every metadata deletion, including cascades."""
from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import StorageDeletionJob, VaultFile
from .services import cleanup_after_commit


@receiver(post_delete, sender=VaultFile, dispatch_uid="vault.queue_private_object_deletion")
def queue_private_object_deletion(sender, instance, using, **kwargs):
    if instance.blob.name:
        StorageDeletionJob.objects.using(using).get_or_create(storage_key=instance.blob.name)
        transaction.on_commit(cleanup_after_commit, using=using)

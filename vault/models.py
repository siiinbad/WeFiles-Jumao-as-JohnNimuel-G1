import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


def private_upload_path(instance, filename):
    return f"objects/{uuid.uuid4().hex}"


def validate_name(value):
    if (
        not value.strip()
        or value.strip() in (".", "..")
        or any(character in value for character in "/\\")
        or any((ord(character) < 32 or ord(character) == 127) for character in value)
    ):
        raise ValidationError("Enter a name without slashes or control characters.")


class Folder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vault_folders"
    )
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    name = models.CharField(max_length=80, validators=[validate_name])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "pk"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                "owner",
                condition=models.Q(parent__isnull=True),
                name="vault_folder_root_ci",
            ),
            models.UniqueConstraint(
                Lower("name"),
                "owner",
                "parent",
                condition=models.Q(parent__isnull=False),
                name="vault_folder_sibling_ci",
            ),
            models.CheckConstraint(
                condition=~models.Q(id=models.F("parent")), name="vault_folder_not_self_parent"
            ),
        ]

    def clean(self):
        super().clean()
        self.name = self.name.strip()
        validate_name(self.name)
        if self.parent_id and self.parent.owner_id != self.owner_id:
            raise ValidationError({"parent": "Choose a folder owned by the same account."})
        seen = {self.pk}
        parent = self.parent
        depth = 0
        while parent:
            if parent.pk in seen or depth >= 12:
                raise ValidationError(
                    {"parent": "Choose a folder outside this folder's descendants (maximum depth: 12)."}
                )
            seen.add(parent.pk)
            depth += 1
            parent = parent.parent

    def __str__(self):
        return self.name


class VaultFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vault_files"
    )
    folder = models.ForeignKey(
        Folder, null=True, blank=True, on_delete=models.PROTECT, related_name="files"
    )
    blob = models.FileField(upload_to=private_upload_path, max_length=100)
    name = models.CharField(max_length=255, validators=[validate_name])
    description = models.CharField(max_length=1000, blank=True)
    size_bytes = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["owner", "created_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(size_bytes__gt=0), name="vault_file_positive_size"
            )
        ]

    def clean(self):
        super().clean()
        self.name = self.name.strip()
        validate_name(self.name)
        if len(self.name) > 255:
            raise ValidationError({"name": "Use a filename of 255 characters or fewer."})
        if self.folder_id and self.folder.owner_id != self.owner_id:
            raise ValidationError({"folder": "Choose a folder owned by the same account."})

    @property
    def extension(self):
        return Path(self.name).suffix.lstrip(".").upper()[:5] or "FILE"

    def __str__(self):
        return self.name


class StorageDeletionJob(models.Model):
    storage_key = models.CharField(max_length=100, unique=True)
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_error_code = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

"""Maintenance is read-only; use the vault UI for validated, owner-checked writes."""
from django.contrib import admin
from accounts.models import User
from .models import Folder, StorageDeletionJob, VaultFile


class VaultInspectionAdmin(admin.ModelAdmin):
    def has_view_permission(self, request, obj=None):
        return request.user.role == User.Role.ADMIN and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(VaultFile)
class VaultFileAdmin(VaultInspectionAdmin):
    list_display = ("name", "owner", "folder", "size_bytes", "created_at")
    search_fields = ("name", "description", "owner__username")
    readonly_fields = ("owner", "folder", "blob", "name", "description", "size_bytes", "content_type", "created_at", "updated_at")


@admin.register(Folder)
class FolderAdmin(VaultInspectionAdmin):
    list_display = ("name", "owner", "parent", "created_at")
    readonly_fields = ("owner", "parent", "name", "created_at", "updated_at")


@admin.register(StorageDeletionJob)
class StorageDeletionJobAdmin(VaultInspectionAdmin):
    list_display = ("storage_key", "attempts", "next_attempt_at", "last_error_code")
    readonly_fields = ("storage_key", "attempts", "next_attempt_at", "last_error_code", "created_at")

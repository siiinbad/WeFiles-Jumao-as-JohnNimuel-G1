"""Role-scoped reads shared by the vault and dashboard presentation."""
from django.db.models import Count, Sum
from accounts.models import User
from .models import Folder, VaultFile


def visible_files(user):
    files = VaultFile.objects.select_related("owner", "folder")
    return files if user.role == User.Role.ADMIN else files.filter(owner=user)


def visible_folders(user):
    folders = Folder.objects.select_related("owner", "parent")
    return folders if user.role == User.Role.ADMIN else folders.filter(owner=user)


def overview_for(user):
    files = visible_files(user)
    stats = files.aggregate(total=Count("pk"), storage=Sum("size_bytes", default=0))
    return {
        "vault_file_count": stats["total"],
        "storage_bytes": stats["storage"],
        "folder_count": visible_folders(user).count(),
        "recent_files": files[:5],
    }

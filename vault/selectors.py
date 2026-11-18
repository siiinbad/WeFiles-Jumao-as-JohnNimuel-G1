"""Role-scoped reads shared by the vault and dashboard presentation."""
from accounts.models import User
from .models import Folder, VaultFile


def visible_files(user):
    files = VaultFile.objects.select_related("owner", "folder")
    return files if user.role == User.Role.ADMIN else files.filter(owner=user)


def visible_folders(user):
    folders = Folder.objects.select_related("owner", "parent")
    return folders if user.role == User.Role.ADMIN else folders.filter(owner=user)

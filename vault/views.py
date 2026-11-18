import logging
import uuid

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.models import User

from .forms import FileForm, FolderForm, UploadForm
from .models import Folder, VaultFile
from .services import delete_file, delete_folder, save_folder, update_file, upload_file

logger = logging.getLogger(__name__)


def visible_files(user):
    files = VaultFile.objects.select_related("owner", "folder")
    return files if user.role == User.Role.ADMIN else files.filter(owner=user)


def visible_folders(user):
    folders = Folder.objects.select_related("owner", "parent")
    return folders if user.role == User.Role.ADMIN else folders.filter(owner=user)


def resolve_uuid(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise Http404("That item could not be found.") from None


@require_http_methods(["GET", "HEAD"])
def file_list(request, folder_id=None):
    folder = None
    if folder_id:
        folder = get_object_or_404(visible_folders(request.user), pk=resolve_uuid(folder_id))
    files = visible_files(request.user).filter(folder=folder)
    folders = visible_folders(request.user).filter(parent=folder)
    return render(request, "vault/list.html", {"files": files, "folders": folders, "folder": folder})


@require_http_methods(["GET", "POST"])
def upload(request):
    initial = {}
    if request.GET.get("folder"):
        initial["folder"] = get_object_or_404(
            Folder.objects.filter(owner=request.user), pk=resolve_uuid(request.GET["folder"])
        )
    form = UploadForm(
        request.POST if request.method == "POST" else None,
        request.FILES or None,
        user=request.user,
        initial=initial,
    )
    if request.method == "POST" and form.is_valid():
        try:
            file = upload_file(
                request.user,
                form.cleaned_data["file"],
                form.cleaned_data["folder"],
                form.cleaned_data["description"],
            )
        except ValidationError as exc:
            form.add_error(None, " ".join(exc.messages))
        except IntegrityError:
            form.add_error(None, "The destination changed. Please try again.")
        except OSError:
            logger.warning("Private file upload failed")
            form.add_error(None, "The file could not be stored. Please try again shortly.")
        else:
            messages.success(request, "Your file has been uploaded.")
            return redirect("vault:detail", pk=file.pk)
    return render(
        request,
        "vault/form.html",
        {"form": form, "title": "Upload a file", "submit_label": "Upload file", "upload": True},
    )


@require_http_methods(["GET", "POST"])
def folder_create(request):
    initial = {}
    if request.GET.get("parent"):
        initial["parent"] = get_object_or_404(
            Folder.objects.filter(owner=request.user),
            pk=resolve_uuid(request.GET["parent"]),
        )
    form = FolderForm(request.POST if request.method == "POST" else None, user=request.user, initial=initial)
    if request.method == "POST" and form.is_valid():
        folder = form.save(commit=False)
        try:
            save_folder(request.user, folder)
        except ValidationError as exc:
            form.add_error(None, " ".join(exc.messages))
        except IntegrityError:
            form.add_error("name", "A folder with this name already exists here.")
        else:
            messages.success(request, "Folder created.")
            return redirect("vault:folder", folder_id=folder.pk)
    return render(
        request,
        "vault/form.html",
        {"form": form, "title": "Create a folder", "submit_label": "Create folder"},
    )


@require_http_methods(["GET", "POST"])
def folder_edit(request, pk):
    folder = get_object_or_404(visible_folders(request.user), pk=resolve_uuid(pk))
    form = FolderForm(request.POST if request.method == "POST" else None, instance=folder, user=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            save_folder(request.user, form.save(commit=False))
        except ValidationError as exc:
            form.add_error(None, " ".join(exc.messages))
        except IntegrityError:
            form.add_error("name", "A folder with this name already exists here.")
        else:
            messages.success(request, "Folder updated.")
            return redirect("vault:folder", folder_id=folder.pk)
    return render(
        request,
        "vault/form.html",
        {"form": form, "title": "Edit folder", "submit_label": "Save changes"},
    )


@require_http_methods(["GET", "HEAD"])
def file_detail(request, pk):
    file = get_object_or_404(visible_files(request.user), pk=resolve_uuid(pk))
    return render(request, "vault/detail.html", {"file": file})


@require_http_methods(["GET", "POST"])
def file_edit(request, pk):
    file = get_object_or_404(visible_files(request.user), pk=resolve_uuid(pk))
    form = FileForm(request.POST if request.method == "POST" else None, instance=file, user=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            update_file(request.user, form.save(commit=False))
        except ValidationError as exc:
            form.add_error(None, " ".join(exc.messages))
        except IntegrityError:
            form.add_error(None, "The destination changed. Please try again.")
        else:
            messages.success(request, "File details updated.")
            return redirect("vault:detail", pk=file.pk)
    return render(
        request,
        "vault/form.html",
        {"form": form, "title": "Edit file details", "submit_label": "Save changes"},
    )


@require_http_methods(["GET", "POST"])
def delete_item(request, pk, item_type):
    queryset = visible_files(request.user) if item_type == "file" else visible_folders(request.user)
    item = get_object_or_404(queryset, pk=resolve_uuid(pk))
    if request.method == "POST":
        if request.POST.get("confirm") != "yes":
            messages.error(request, "Please confirm the deletion.")
        else:
            try:
                (delete_file if item_type == "file" else delete_folder)(request.user, item)
            except ValidationError as exc:
                messages.error(request, " ".join(exc.messages))
            else:
                messages.success(request, f"{item_type.title()} deleted.")
                return redirect("vault:list")
    return render(request, "vault/confirm_delete.html", {"object": item, "item_type": item_type})


@require_http_methods(["GET", "HEAD"])
def download(request, pk):
    file = get_object_or_404(visible_files(request.user), pk=resolve_uuid(pk))
    try:
        response = FileResponse(
            file.blob.open("rb"),
            as_attachment=True,
            filename=file.name,
            content_type="application/octet-stream",
        )
    except (FileNotFoundError, OSError):
        logger.warning("A private download object was unavailable")
        raise Http404("This file is unavailable. Please contact an administrator.") from None
    response["X-Content-Type-Options"] = "nosniff"
    return response

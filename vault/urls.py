from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views

app_name = "vault"
urlpatterns = [
    path("", login_required(views.file_list), name="list"),
    path("upload/", login_required(views.upload), name="upload"),
    path("folders/new/", login_required(views.folder_create), name="folder_create"),
    path("folders/<uuid:folder_id>/", login_required(views.file_list), name="folder"),
    path("folders/<uuid:pk>/edit/", login_required(views.folder_edit), name="folder_edit"),
    path(
        "folders/<uuid:pk>/delete/",
        login_required(lambda request, pk: views.delete_item(request, pk, "folder")),
        name="folder_delete",
    ),
    path("files/<uuid:pk>/", login_required(views.file_detail), name="detail"),
    path("files/<uuid:pk>/download/", login_required(views.download), name="download"),
    path("files/<uuid:pk>/edit/", login_required(views.file_edit), name="edit"),
    path(
        "files/<uuid:pk>/delete/",
        login_required(lambda request, pk: views.delete_item(request, pk, "file")),
        name="delete",
    ),
]

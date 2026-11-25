from django.urls import path

from . import views

app_name = "vault"
urlpatterns = [
    path("", views.file_list, name="list"),
    path("upload/", views.upload, name="upload"),
    path("folders/new/", views.folder_create, name="folder_create"),
    path("folders/<uuid:folder_id>/", views.file_list, name="folder"),
    path("folders/<uuid:pk>/edit/", views.folder_edit, name="folder_edit"),
    path(
        "folders/<uuid:pk>/delete/",
        views.folder_delete,
        name="folder_delete",
    ),
    path("files/<uuid:pk>/", views.file_detail, name="detail"),
    path("files/<uuid:pk>/download/", views.download, name="download"),
    path("files/<uuid:pk>/edit/", views.file_edit, name="edit"),
    path(
        "files/<uuid:pk>/delete/",
        views.file_delete,
        name="delete",
    ),
]

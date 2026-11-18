from django import forms
from django.conf import settings

from .models import Folder, VaultFile, validate_name


class FolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ["name", "parent"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance._state.adding:
            self.instance.owner = user
        owner_id = self.instance.owner_id
        parent_folders = Folder.objects.filter(owner_id=owner_id)
        self.fields["parent"].queryset = parent_folders
        self.fields["parent"].empty_label = "Vault root"
        if self.instance.pk:
            self.fields["parent"].queryset = self.fields["parent"].queryset.exclude(
                pk=self.instance.pk
            )

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        validate_name(name)
        return name


class UploadForm(forms.Form):
    file = forms.FileField()
    folder = forms.ModelChoiceField(
        queryset=Folder.objects.none(), required=False, empty_label="Vault root"
    )
    description = forms.CharField(
        max_length=1000, required=False, widget=forms.Textarea(attrs={"rows": 3})
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["folder"].queryset = Folder.objects.filter(owner_id=user.pk)
        self.fields["file"].help_text = (
            f"One file at a time, up to {settings.MAX_UPLOAD_BYTES // 1024 // 1024} MiB."
        )

    def clean_file(self):
        upload = self.cleaned_data["file"]
        validate_name(upload.name)
        if len(upload.name) > 255:
            raise forms.ValidationError("Use a filename of 255 characters or fewer.")
        if upload.size == 0:
            raise forms.ValidationError("That file is empty. Choose a file with some content.")
        if upload.size > settings.MAX_UPLOAD_BYTES:
            limit = settings.MAX_UPLOAD_BYTES // 1024 // 1024
            raise forms.ValidationError(f"Choose a file smaller than {limit} MiB.")
        return upload


class FileForm(forms.ModelForm):
    class Meta:
        model = VaultFile
        fields = ["name", "description", "folder"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        owner_id = self.instance.owner_id or user.pk
        self.fields["folder"].queryset = Folder.objects.filter(owner_id=owner_id)
        self.fields["folder"].required = False
        self.fields["folder"].empty_label = "Vault root"

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        validate_name(name)
        return name

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(help_text="Use an email address you own.")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_username(self):
        value = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=value).exists():
            raise forms.ValidationError("This username is already in use.")
        return value

    def clean_email(self):
        value = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise forms.ValidationError("This email address is already in use.")
        return value

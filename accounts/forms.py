from django import forms
from django.contrib.auth.forms import AuthenticationForm as DjangoAuthenticationForm, UserCreationForm
from .models import User


class AuthenticationForm(DjangoAuthenticationForm):
    def get_invalid_login_error(self):
        # Give a recovery hint without revealing whether a username exists.
        return forms.ValidationError([
            *super().get_invalid_login_error().messages,
            "Your account must also be approved and active to sign in. Contact a workspace Admin if needed.",
        ], code="invalid_login")


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

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.MEMBER
        user.account_status = User.AccountStatus.PENDING
        user.is_active = False
        if commit:
            user.save()
        return user


class AccountAccessForm(forms.Form):
    role = forms.ChoiceField(choices=User.Role.choices)
    account_status = forms.ChoiceField(
        label="Account status", choices=User.AccountStatus.choices,
        help_text="Approved allows sign-in. Pending, Rejected and Inactive block access.",
    )
    version = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    confirm = forms.BooleanField(label="I confirm this account access change.")


class ProfileForm(forms.ModelForm):
    """Only these contact fields may change; never accept user IDs or roles."""
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        labels = {"first_name": "First name", "last_name": "Last name"}
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

    def clean_email(self):
        value = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email address is already in use.")
        return value

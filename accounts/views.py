from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from .forms import RegistrationForm


@require_http_methods(["GET", "HEAD"])
def home(request):
    return render(request, "home.html")


@require_http_methods(["GET", "POST"])
def register(request):
    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError:
            form.add_error(None, "That username or email was just registered. Choose another.")
        else:
            messages.success(request, "Your account has been created successfully.")
            return redirect("accounts:registered")
    return render(request, "accounts/register.html", {"form": form})


def registered(request):
    return render(request, "accounts/registered.html")


def forbidden(request, exception=None):
    return render(request, "errors/error.html", {"code": 403, "reason": "You do not have permission to open this page."}, status=403)


def not_found(request, exception=None):
    return render(request, "errors/error.html", {"code": 404, "reason": "This page could not be found."}, status=404)


def server_error(request):
    return render(request, "errors/error.html", {"code": 500, "reason": "We could not complete that request. Please try again later."}, status=500)

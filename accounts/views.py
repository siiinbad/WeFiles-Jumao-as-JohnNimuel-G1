from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST
from .forms import ProfileForm, RegistrationForm
from .models import User
from .permissions import role_required


@require_http_methods(["GET", "HEAD"])
def home(request):
    return render(request, "home.html")


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
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


@require_http_methods(["GET", "POST"])
def login(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = AuthenticationForm(request, data=request.POST if request.method == "POST" else None)
    next_url = request.POST.get("next", "") if request.method == "POST" else request.GET.get("next", "")
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = ""
    if request.method == "POST" and form.is_valid():
        auth_login(request, form.get_user())
        messages.success(request, "You are now signed in.")
        return redirect(next_url or "accounts:dashboard")
    return render(request, "accounts/login.html", {"form": form, "next": next_url})


@require_POST
@login_required
def logout(request):
    auth_logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("accounts:login")


@login_required
@require_http_methods(["GET", "HEAD"])
def dashboard(request):
    if request.user.role == User.Role.ADMIN:
        return redirect("accounts:admin_dashboard")
    if request.user.role == User.Role.MEMBER:
        return redirect("accounts:member_dashboard")
    raise PermissionDenied


@login_required
@role_required(User.Role.MEMBER)
@require_http_methods(["GET", "HEAD"])
def member_dashboard(request):
    return render(request, "accounts/member_dashboard.html")


@login_required
@role_required(User.Role.ADMIN)
@require_http_methods(["GET", "HEAD"])
def admin_dashboard(request):
    counts = User.objects.aggregate(
        total=Count("pk"),
        members=Count("pk", filter=Q(role=User.Role.MEMBER)),
        admins=Count("pk", filter=Q(role=User.Role.ADMIN)),
    )
    recent_users = User.objects.order_by("-date_joined", "-pk")[:5]
    return render(request, "accounts/admin_dashboard.html", {"counts": counts, "recent_users": recent_users})


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    form = ProfileForm(
        request.POST if request.method == "POST" else None,
        instance=request.user,
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError:
            form.add_error("email", "This email address was just registered. Choose another.")
        else:
            messages.success(request, "Your profile has been updated.")
            return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})


def forbidden(request, exception=None):
    return render(request, "errors/error.html", {"code": 403, "reason": "You do not have permission to open this page."}, status=403)


def not_found(request, exception=None):
    return render(request, "errors/error.html", {"code": 404, "reason": "This page could not be found."}, status=404)


def server_error(request):
    # Do not query a user's session while handling a possible database outage.
    return render(None, "errors/error.html", {"code": 500, "reason": "We could not complete that request. Please try again later."}, status=500)

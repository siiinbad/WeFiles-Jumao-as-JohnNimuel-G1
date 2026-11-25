from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST
from .forms import AccountAccessForm, AuthenticationForm, ProfileForm, RegistrationForm
from .models import User
from .permissions import role_required
from .services import change_account_access
from vault.selectors import overview_for


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
            messages.success(request, "Your account has been created and is pending Admin approval.")
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
@role_required(User.Role.ADMIN, User.Role.MEMBER)
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
    return render(
        request,
        "accounts/member_dashboard.html",
        overview_for(request.user),
    )


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
    return render(
        request,
        "accounts/admin_dashboard.html",
        {
            "counts": counts,
            "recent_users": recent_users,
            "pending_count": User.objects.filter(account_status=User.AccountStatus.PENDING).count(),
            **overview_for(request.user),
        },
    )


@login_required
@role_required(User.Role.ADMIN, User.Role.MEMBER)
@require_http_methods(["GET", "POST"])
def profile(request):
    form = ProfileForm(
        request.POST if request.method == "POST" else None,
        instance=request.user,
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save(commit=False).save(update_fields=["first_name", "last_name", "email"])
        except IntegrityError:
            form.add_error("email", "This email address was just registered. Choose another.")
        else:
            messages.success(request, "Your profile has been updated.")
            return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})


@login_required
@role_required(User.Role.ADMIN)
@require_http_methods(["GET", "HEAD"])
def account_list(request):
    accounts = User.objects.order_by("-date_joined", "-pk")
    page = Paginator(accounts, 25).get_page(request.GET.get("page"))
    return render(request, "accounts/account_list.html", {"page_obj": page})


@login_required
@role_required(User.Role.ADMIN)
@require_http_methods(["GET", "POST"])
def account_access(request, pk):
    account = get_object_or_404(User, pk=pk)
    protected = account.pk == request.user.pk or account.is_staff or account.is_superuser
    form = AccountAccessForm(
        request.POST if request.method == "POST" else None,
        initial={"role": account.role, "account_status": account.account_status, "version": account.session_version},
    )
    if request.method == "POST" and form.is_valid():
        try:
            account = change_account_access(
                request.user, account.pk, role=form.cleaned_data["role"],
                account_status=form.cleaned_data["account_status"], version=form.cleaned_data["version"],
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, f"Access updated for {account.username}: {account.get_role_display()}, {account.get_account_status_display()}.")
            return redirect("accounts:account_list")
    return render(request, "accounts/account_access.html", {"account": account, "form": form, "protected": protected})


def forbidden(request, exception=None):
    return render(request, "errors/error.html", {"code": 403, "reason": "You do not have permission to open this page."}, status=403)


def not_found(request, exception=None):
    return render(request, "errors/error.html", {"code": 404, "reason": "This page could not be found."}, status=404)


def server_error(request):
    # Do not query a user's session while handling a possible database outage.
    return render(None, "errors/error.html", {"code": 500, "reason": "We could not complete that request. Please try again later."}, status=500)

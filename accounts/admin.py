from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class WorkspaceUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("WeFiles access", {"fields": ("role", "account_status")}),)
    list_display = ("username", "email", "role", "account_status", "is_staff")
    list_filter = UserAdmin.list_filter + ("role", "account_status")

    # Keep account mutations on the guarded workspace form. Maintenance users
    # remain inspectable here; bootstrap/password recovery use operator commands.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

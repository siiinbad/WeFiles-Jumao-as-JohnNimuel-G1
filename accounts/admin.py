from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class WorkspaceUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("WeFiles role", {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = UserAdmin.list_filter + ("role",)

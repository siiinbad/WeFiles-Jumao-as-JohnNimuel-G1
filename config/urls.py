from django.contrib import admin
from django.urls import include, path
from accounts import views
from .health import health

urlpatterns = [
    path("health/", health, name="health"),
    path("", views.home, name="home"),
    path("accounts/", include("accounts.urls")),
    path("vault/", include("vault.urls")),
    path("maintenance/", admin.site.urls),
]
handler403 = "accounts.views.forbidden"
handler404 = "accounts.views.not_found"
handler500 = "accounts.views.server_error"

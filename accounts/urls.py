from django.urls import path
from . import views

app_name = "accounts"
urlpatterns = [
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/member/", views.member_dashboard, name="member_dashboard"),
    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("register/", views.register, name="register"),
    path("registered/", views.registered, name="registered"),
]

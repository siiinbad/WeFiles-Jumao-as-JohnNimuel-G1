from django.urls import path
from . import views

app_name = "accounts"
urlpatterns = [
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/member/", views.member_dashboard, name="member_dashboard"),
    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("profile/", views.profile, name="profile"),
    path("manage/", views.account_list, name="account_list"),
    path("manage/<int:pk>/", views.account_access, name="account_access"),
    path("register/", views.register, name="register"),
    path("registered/", views.registered, name="registered"),
]

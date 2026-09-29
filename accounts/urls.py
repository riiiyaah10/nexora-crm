from django.urls import path
from . import views

app_name = "accounts"
urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("verify/", views.verify_view, name="verify"),

    path("register/", views.register_view, name="register"),
    path(
        "register/verify/",
        views.register_verify_view,
        name="register_verify"
    ),

    path("logout/", views.logout_view, name="logout"),
    path("users/", views.user_list, name="users"),
    path("users/new/", views.user_edit, name="user_new"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("roles/", views.roles, name="roles"),
    path("audit/", views.audit_log, name="audit"),
]
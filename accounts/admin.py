from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CRMUserAdmin(UserAdmin):
    ordering = ("email",)
    list_display = ("email", "name", "is_active", "is_staff")
    fieldsets = ((None, {"fields": ("email", "name", "password")}),
                 ("Access", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}))
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "name", "password1", "password2")}),)
    search_fields = ("email", "name")

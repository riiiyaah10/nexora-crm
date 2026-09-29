from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("leads/", include("leads.urls")),
    path("projects/", include("projects.urls")),
    path("finance/", include("finance.urls")),
    path("crm/", include("crm.urls")),
]

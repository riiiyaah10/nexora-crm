from django.urls import path
from . import views

app_name = "leads"
urlpatterns = [
    path("", views.lead_list, name="list"),
    path("new/", views.lead_create, name="create"),
    path("export/", views.lead_export, name="export"),
    path("<int:pk>/", views.lead_detail, name="detail"),
    path("<int:pk>/edit/", views.lead_update, name="update"),
    path("<int:pk>/delete/", views.lead_delete, name="delete"),
    path("<int:pk>/status/", views.lead_status, name="status"),
    path("<int:pk>/activity/", views.lead_activity, name="activity"),
    path("<int:pk>/convert/", views.lead_convert, name="convert"),
]

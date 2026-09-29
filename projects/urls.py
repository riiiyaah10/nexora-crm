from django.urls import path
from . import views

app_name = "projects"
urlpatterns = [
    path("", views.project_list, name="list"),
    path("new/", views.project_create, name="create"),
    path("<int:pk>/", views.project_detail, name="detail"),
    path("<int:pk>/edit/", views.project_update, name="update"),
    path("<int:pk>/delete/", views.project_delete, name="delete"),
    path("<int:pk>/status/", views.project_status, name="status"),
]

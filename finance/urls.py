from django.urls import path
from . import views

app_name = "finance"
urlpatterns = [
    path("", views.overview, name="overview"),
    path("invoices/", views.invoice_list, name="invoices"),
    path("invoices/new/", views.invoice_create, name="invoice_create"),
    path("invoices/<int:pk>/edit/", views.invoice_update, name="invoice_update"),
    path("invoices/<int:pk>/status/", views.invoice_status, name="invoice_status"),
    path("invoices/<int:pk>/delete/", views.invoice_delete, name="invoice_delete"),
    path("transactions/", views.transaction_list, name="transactions"),
    path("transactions/new/", views.transaction_create, name="transaction_create"),
    path("transactions/<int:pk>/delete/", views.transaction_delete, name="transaction_delete"),
]

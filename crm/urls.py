from django.urls import path
from . import views

app_name = "crm"

urlpatterns = [
    # Companies
    path("companies/", views.company_list, name="company_list"),
    path("companies/new/", views.company_create, name="company_create"),
    path("companies/<int:pk>/", views.company_detail, name="company_detail"),
    path("companies/<int:pk>/edit/", views.company_update, name="company_update"),
    path("companies/<int:pk>/delete/", views.company_delete, name="company_delete"),
    path("companies/export/", views.export_companies_csv, name="export_companies_csv"),
    path("export/companies/", views.export_companies_csv),

    # Contacts
    path("contacts/", views.contact_list, name="contact_list"),
    path("contacts/new/", views.contact_create, name="contact_create"),
    path("contacts/<int:pk>/", views.contact_detail, name="contact_detail"),
    path("contacts/<int:pk>/edit/", views.contact_update, name="contact_update"),
    path("contacts/<int:pk>/delete/", views.contact_delete, name="contact_delete"),
    path("contacts/export/", views.export_contacts_csv, name="export_contacts_csv"),
    path("export/contacts/", views.export_contacts_csv),

    # Unified Activities
    path("activities/new/", views.activity_create, name="activity_create"),

    # CRM Calendar & Reports
    path("calendar/", views.calendar_view, name="calendar"),
    path("reports/", views.reports_view, name="reports"),

    # Omnisearch & Navigation API
    path("search/", views.search_view, name="search"),
    path("api/search/", views.api_search, name="api_search"),

    # Notifications
    path("notifications/", views.notification_list, name="notifications"),
    path("notifications/<int:pk>/read/", views.notification_mark_read, name="notification_mark_read"),
    path("notifications/read-all/", views.notification_read_all, name="notification_read_all"),

    # CSV Import
    path("import/", views.import_csv, name="import_csv"),
]

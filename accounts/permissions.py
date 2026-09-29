"""CRM permission catalogue and default company roles."""

from functools import reduce
from operator import or_

from django.contrib.auth.models import Permission
from django.db.models import Q


MODULE_PERMS = {
    "Dashboard": [
        ("core.view_dashboard", "View dashboard"),
    ],

    "Leads": [
        ("leads.view_lead", "View leads"),
        ("leads.add_lead", "Add leads"),
        ("leads.change_lead", "Edit leads & log activity"),
        ("leads.delete_lead", "Delete leads"),
        ("leads.view_all_leads", "See ALL leads"),
    ],

    "Contacts": [
        ("crm.view_contact", "View contacts"),
        ("crm.add_contact", "Add contacts"),
        ("crm.change_contact", "Edit contacts"),
        ("crm.delete_contact", "Delete contacts"),
    ],

    "Companies": [
        ("crm.view_company", "View companies"),
        ("crm.add_company", "Add companies"),
        ("crm.change_company", "Edit companies"),
        ("crm.delete_company", "Delete companies"),
    ],

    "Projects": [
        ("projects.view_project", "View projects"),
        ("projects.add_project", "Add projects"),
        ("projects.change_project", "Edit projects"),
        ("projects.delete_project", "Delete projects"),
    ],

    "Finance": [
        ("finance.view_finance", "View finance"),
        ("finance.add_invoice", "Create invoices"),
        ("finance.change_invoice", "Edit invoices / mark sent & paid"),
        ("finance.delete_invoice", "Delete invoices"),
        ("finance.add_transaction", "Add income / expenses"),
        ("finance.delete_transaction", "Delete income / expenses"),
    ],

    "Reports & Analytics": [
        ("crm.view_reports", "View CRM analytics & reports"),
    ],

    "Administration": [
        ("accounts.manage_users", "Manage users, roles & audit log"),
    ],
}


ALL_CODES = [
    code
    for items in MODULE_PERMS.values()
    for code, _ in items
]


# ---------------------------------------------------------
# DEFAULT COMPANY ROLES
# ---------------------------------------------------------

DEFAULT_ROLES = {

    "Admin": ALL_CODES,

    "Sales Manager": [
        "core.view_dashboard",

        "leads.view_lead",
        "leads.add_lead",
        "leads.change_lead",
        "leads.delete_lead",
        "leads.view_all_leads",

        "crm.view_contact",
        "crm.add_contact",
        "crm.change_contact",
        "crm.delete_contact",

        "crm.view_company",
        "crm.add_company",
        "crm.change_company",
        "crm.delete_company",

        "crm.view_reports",

        "projects.view_project",
    ],

    "Sales Executive": [
        "core.view_dashboard",

        "leads.view_lead",
        "leads.add_lead",
        "leads.change_lead",

        "crm.view_contact",
        "crm.add_contact",
        "crm.change_contact",

        "crm.view_company",
    ],

    "Project Manager": [
        "core.view_dashboard",

        "projects.view_project",
        "projects.add_project",
        "projects.change_project",
        "projects.delete_project",

        "leads.view_lead",
        "leads.view_all_leads",

        "crm.view_contact",
        "crm.view_company",
    ],

    "Finance": [
        "core.view_dashboard",

        "finance.view_finance",
        "finance.add_invoice",
        "finance.change_invoice",
        "finance.add_transaction",
        "finance.delete_transaction",

        "crm.view_company",
        "crm.view_reports",

        "projects.view_project",
    ],

    "Viewer": [
        "core.view_dashboard",
        "leads.view_lead",
        "crm.view_contact",
        "crm.view_company",
        "projects.view_project",
        "crm.view_reports",
    ],
}


def perm_objects(codes):
    pairs = [
        code.split(".", 1)
        for code in codes
        if code in ALL_CODES
    ]

    if not pairs:
        return Permission.objects.none()

    conditions = [
        Q(content_type__app_label=app_label, codename=codename)
        for app_label, codename in pairs
    ]

    return Permission.objects.filter(
        reduce(or_, conditions)
    )


def codes_of(perm_qs):
    return {
        f"{p.content_type.app_label}.{p.codename}"
        for p in perm_qs.select_related("content_type")
    }


def grid(checked):
    """Structure used by the permission-checkbox template."""
    return [
        (
            module,
            [
                (code, label, code in checked)
                for code, label in items
            ],
        )
        for module, items in MODULE_PERMS.items()
    ]
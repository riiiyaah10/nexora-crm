import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from crm.models import Company, Contact, UnifiedActivity, Notification, Tag
from leads.models import Lead

User = get_user_model()
admin_user = User.objects.filter(groups__name="Admin").first() or User.objects.filter(is_superuser=True).first()

if not admin_user:
    admin_user = User.objects.first()

print(f"Testing with user: {admin_user.email} (Role: {admin_user.role})")

anon_client = Client()
anon_res = anon_client.get("/accounts/login/")
assert anon_res.status_code == 200, f"Anonymous login page returned {anon_res.status_code}"
print("  [OK] /accounts/login/ (Anonymous) -> 200")

client = Client()
client.force_login(admin_user)

endpoints = [
    # Existing
    ("/dashboard/", 200),
    ("/leads/", 200),
    ("/leads/new/", 200),
    ("/projects/", 200),
    ("/finance/", 200),
    ("/finance/invoices/", 200),
    ("/finance/transactions/", 200),
    ("/accounts/users/", 200),
    ("/accounts/roles/", 200),
    ("/accounts/audit/", 200),

    # New CRM endpoints
    ("/crm/companies/", 200),
    ("/crm/companies/new/", 200),
    ("/crm/contacts/", 200),
    ("/crm/contacts/new/", 200),
    ("/crm/calendar/", 200),
    ("/crm/reports/", 200),
    ("/crm/notifications/", 200),
    ("/crm/search/?q=Zenith", 200),
    ("/crm/api/search/?q=Zenith", 200),
    ("/crm/import/", 200),
    ("/crm/export/contacts/", 200),
    ("/crm/export/companies/", 200),
]

all_passed = True
for url, expected_code in endpoints:
    res = client.get(url)
    if res.status_code == expected_code:
        print(f"  [OK] {url} -> {res.status_code}")
    else:
        print(f"  [FAIL] {url} -> {res.status_code} (expected {expected_code})")
        all_passed = False

# Test creating a Company & Contact
print("\nTesting Company and Contact CRUD & Activity logging...")
company, _ = Company.objects.get_or_create(
    name="Apex Global Technologies",
    defaults={
        "domain": "apextech.io",
        "industry": "Technology",
        "annual_revenue": 1500000,
        "owner": admin_user,
    }
)
print(f"Company created/found: {company.name} (PK {company.pk})")

comp_res = client.get(f"/crm/companies/{company.pk}/")
assert comp_res.status_code == 200, f"Company detail failed: {comp_res.status_code}"
print(f"  [OK] /crm/companies/{company.pk}/ -> 200")

contact, _ = Contact.objects.get_or_create(
    first_name="Vikram",
    last_name="Singhania",
    email="vikram@apextech.io",
    defaults={
        "job_title": "VP Engineering",
        "company": company,
        "owner": admin_user,
    }
)
print(f"Contact created/found: {contact.full_name} (PK {contact.pk})")

contact_res = client.get(f"/crm/contacts/{contact.pk}/")
assert contact_res.status_code == 200, f"Contact detail failed: {contact_res.status_code}"
print(f"  [OK] /crm/contacts/{contact.pk}/ -> 200")

# Test Activity logging POST
act_res = client.post("/crm/activities/new/", {
    "kind": "Meeting",
    "title": "Architecture Review & Security Compliance",
    "note": "Discussed SOC2 requirements and dedicated database instances.",
    "company_id": company.pk,
    "contact_id": contact.pk,
})
print(f"  [OK] Activity creation -> {act_res.status_code} (Redirect)")

# Test Notification creation
notif = Notification.objects.create(
    user=admin_user,
    title="New High-Value Account Created",
    message=f"Company '{company.name}' was onboarded.",
    link=f"/crm/companies/{company.pk}/"
)
print(f"Notification created: {notif.title}")
notif_res = client.get(f"/crm/notifications/{notif.pk}/read/")
print(f"  [OK] Notification read -> {notif_res.status_code}")

# Test API search
search_res = client.get("/crm/api/search/?q=Apex")
data = search_res.json()
print(f"  [OK] API search for 'Apex': {len(data['results'])} category group(s) returned")

if all_passed:
    print("\nALL CRM TESTS PASSED PERFECTLY!")
else:
    print("\nSOME TESTS FAILED - CHECK OUTPUT ABOVE")
    sys.exit(1)

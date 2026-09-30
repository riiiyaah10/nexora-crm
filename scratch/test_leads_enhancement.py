import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from leads.models import Lead, SOURCES, LEAD_TYPES
from leads.views import _filtered

User = get_user_model()
admin_user = User.objects.filter(groups__name="Admin").first() or User.objects.filter(is_superuser=True).first() or User.objects.first()

client = Client()
client.force_login(admin_user)
rf = RequestFactory()

print("==================================================")
print("TEST 1: CREATE LEAD (Rahul Sharma, Instagram, Organic)")
print("==================================================")
# Clean up any existing test lead
Lead.objects.filter(name="Rahul Sharma").delete()

res_create = client.post("/leads/new/", {
    "name": "Rahul Sharma",
    "phone": "+91 98765 43210",
    "email": "rahul@example.com",
    "company": "Sharma Tech Enterprises",
    "source": "Instagram",
    "lead_type": "Organic",
    "status": "New",
    "value": "75000",
})
assert res_create.status_code == 302, f"Expected 302 redirect, got {res_create.status_code}"

lead = Lead.objects.filter(name="Rahul Sharma").first()
assert lead is not None, "Lead 'Rahul Sharma' was not created in DB!"
assert lead.phone == "+91 98765 43210"
assert lead.email == "rahul@example.com"
assert lead.source == "Instagram", f"Expected 'Instagram', got '{lead.source}'"
assert lead.lead_type == "Organic", f"Expected 'Organic', got '{lead.lead_type}'"
print("  [PASS] Created Lead successfully: Name='Rahul Sharma', Source='Instagram', Type='Organic' (PK:", lead.pk, ")")

print("\n==================================================")
print("TEST 2: VERIFY LEAD DETAIL PAGE")
print("==================================================")
detail_res = client.get(f"/leads/{lead.pk}/")
assert detail_res.status_code == 200
html = detail_res.content.decode()

assert "Rahul Sharma" in html, "Lead Name missing in detail HTML"
assert "+91 98765 43210" in html, "Phone number missing in detail HTML"
assert "rahul@example.com" in html, "Email address missing in detail HTML"
assert "Instagram" in html, "Source 'Instagram' missing in detail HTML"
assert "Organic" in html, "Type 'Organic' missing in detail HTML"
assert "type-organic" in html, "type-organic badge class missing in detail HTML"
assert "source-chip" in html, "source-chip class missing in detail HTML"
print("  [PASS] Detail page correctly renders Name, Phone, Email, Source badge, and Type badge.")

print("\n==================================================")
print("TEST 3: EDIT LEAD (Change Source to Google, Type to Junk)")
print("==================================================")
edit_res = client.post(f"/leads/{lead.pk}/edit/", {
    "name": "Rahul Sharma",
    "phone": "+91 98765 43210",
    "email": "rahul@example.com",
    "company": "Sharma Tech Enterprises",
    "source": "Google",
    "lead_type": "Junk",
    "status": "Contacted",
    "value": "75000",
})
assert edit_res.status_code == 302, f"Expected 302 redirect, got {edit_res.status_code}"

lead.refresh_from_db()
assert lead.source == "Google", f"Expected Source='Google', got '{lead.source}'"
assert lead.lead_type == "Junk", f"Expected Type='Junk', got '{lead.lead_type}'"
assert lead.status == "Contacted"

detail_res2 = client.get(f"/leads/{lead.pk}/")
html2 = detail_res2.content.decode()
assert "Google" in html2
assert "Junk" in html2
assert "type-junk" in html2
print("  [PASS] Edited Lead successfully persisted: Source='Google', Type='Junk'.")

print("\n==================================================")
print("TEST 4: FILTERING BY SOURCE AND LEAD TYPE")
print("==================================================")
# Create test leads for each supported source
for src in SOURCES:
    Lead.objects.get_or_create(
        name=f"Lead from {src}",
        defaults={"source": src, "lead_type": "Organic", "status": "New", "value": 10000}
    )
Lead.objects.get_or_create(
    name="Junk Lead from Website",
    defaults={"source": "Website", "lead_type": "Junk", "status": "New", "value": 5000}
)

# Test queryset level filtering via _filtered
for src in SOURCES:
    req = rf.get(f"/leads/?source={src}")
    req.user = admin_user
    qs, q, status, source, lead_type = _filtered(req)
    assert source == src
    assert qs.count() > 0
    for l in qs:
        assert l.source == src, f"Expected source {src}, got {l.source}"
    print(f"  [PASS] Filter by Source='{src}' correctly returned {qs.count()} lead(s).")

# Test filtering by lead_type = Organic
req_org = rf.get("/leads/?lead_type=Organic")
req_org.user = admin_user
qs_org, _, _, _, lt = _filtered(req_org)
assert lt == "Organic"
for l in qs_org:
    assert l.lead_type == "Organic", f"Expected lead_type Organic, got {l.lead_type}"
print(f"  [PASS] Filter by Type='Organic' correctly returned {qs_org.count()} lead(s).")

# Test filtering by lead_type = Junk
req_junk = rf.get("/leads/?lead_type=Junk")
req_junk.user = admin_user
qs_junk, _, _, _, lt_j = _filtered(req_junk)
assert lt_j == "Junk"
assert qs_junk.count() > 0
for l in qs_junk:
    assert l.lead_type == "Junk", f"Expected lead_type Junk, got {l.lead_type}"
print(f"  [PASS] Filter by Type='Junk' correctly returned {qs_junk.count()} lead(s).")

print("\n==================================================")
print("TEST 5: SEARCH & COMBINED FILTERS")
print("==================================================")
req_comb = rf.get("/leads/?q=Rahul&source=Google&lead_type=Junk")
req_comb.user = admin_user
qs_comb, q_c, st_c, src_c, lt_c = _filtered(req_comb)
assert qs_comb.count() == 1
assert qs_comb.first().name == "Rahul Sharma"
assert qs_comb.first().source == "Google"
assert qs_comb.first().lead_type == "Junk"
print("  [PASS] Combined filter (Query='Rahul' + Source='Google' + Type='Junk') matched exact lead.")

# Verify HTML list view table
list_res = client.get("/leads/?source=Google")
assert list_res.status_code == 200
html_list = list_res.content.decode()
assert "Rahul Sharma" in html_list
assert "source-chip" in html_list
assert "type-junk" in html_list
assert "All Sources" in html_list
assert "All Types" in html_list
print("  [PASS] Leads table view renders HTML with source and type columns and filters.")

print("\n==================================================")
print("TEST 6: CSV EXPORT WITH SOURCE & TYPE")
print("==================================================")
export_res = client.get("/leads/export/?source=Google")
assert export_res.status_code == 200
csv_text = export_res.content.decode()
assert "Source" in csv_text and "Type" in csv_text
assert "Google" in csv_text and "Junk" in csv_text
print("  [PASS] CSV export includes Source and Type columns.")

print("\n==================================================")
print("TEST 7: PRESERVATION OF EXISTING LEADS")
print("==================================================")
old_leads = Lead.objects.filter(pk__in=[1, 2])
assert old_leads.count() > 0
for ol in old_leads:
    assert ol.lead_type in ["Organic", "Junk"]
    print(f"  [PASS] Existing Lead #{ol.pk} ('{ol.name}') preserved with Type='{ol.lead_type}'")

print("\n==================================================")
print("ALL LEADS ENHANCEMENT TESTS PASSED 100%!")
print("==================================================")

"""Services for Demo Mode provisioning and idempotent demo data seeding."""

from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from accounts.permissions import DEFAULT_ROLES, perm_objects


DEMO_EMAIL = "demo.viewer@nexora.internal"
DEMO_NAME = "Demo Viewer"


def setup_demo_viewer_role():
    """
    Ensure the 'Demo Viewer' Django Group exists with restricted read-only permissions:
    core.view_dashboard, leads.view_lead, crm.view_contact, crm.view_company, projects.view_project.
    """
    group, _ = Group.objects.get_or_create(name="Demo Viewer")
    perm_codes = DEFAULT_ROLES.get("Demo Viewer", [])
    perms = perm_objects(perm_codes)
    group.permissions.set(perms)
    return group


def ensure_demo_dataset(demo_user):
    """
    Idempotently seeds a clean, realistic, professional demo dataset for Demo Mode:
    - 3 Companies
    - 3 Contacts
    - 5 Leads (across Instagram, Google, Website, Facebook, Organic; Organic & Junk)
    - 2 Projects
    - 4 Tasks
    Adheres strictly to the Global Demo Data Policy (small dataset, no duplication).
    """
    from crm.models import Company, Contact
    from leads.models import Lead
    from projects.models import Project
    from core.models import Task

    today = timezone.localdate()

    # 1. Companies (3 records)
    c1, _ = Company.objects.get_or_create(
        name="Acme Cloud Solutions",
        defaults={
            "domain": "acmecloud.io",
            "industry": "Technology",
            "website": "https://acmecloud.io",
            "phone": "+1 555-0199",
            "email": "contact@acmecloud.io",
            "annual_revenue": Decimal("12500000.00"),
            "owner": demo_user,
        }
    )

    c2, _ = Company.objects.get_or_create(
        name="Starlight Media Group",
        defaults={
            "domain": "starlightmedia.com",
            "industry": "Consulting",
            "website": "https://starlightmedia.com",
            "phone": "+1 555-0144",
            "email": "info@starlightmedia.com",
            "annual_revenue": Decimal("8200000.00"),
            "owner": demo_user,
        }
    )

    c3, _ = Company.objects.get_or_create(
        name="Vanguard Health Systems",
        defaults={
            "domain": "vanguardhealth.org",
            "industry": "Healthcare",
            "website": "https://vanguardhealth.org",
            "phone": "+1 555-0182",
            "email": "hello@vanguardhealth.org",
            "annual_revenue": Decimal("24000000.00"),
            "owner": demo_user,
        }
    )

    # 2. Contacts (3 records)
    Contact.objects.get_or_create(
        email="sarah.jenkins@acmecloud.io",
        defaults={
            "first_name": "Sarah",
            "last_name": "Jenkins",
            "phone": "+1 555-0191",
            "job_title": "VP of Engineering",
            "company": c1,
            "owner": demo_user,
        }
    )

    Contact.objects.get_or_create(
        email="marcus.brody@starlightmedia.com",
        defaults={
            "first_name": "Marcus",
            "last_name": "Brody",
            "phone": "+1 555-0142",
            "job_title": "Managing Director",
            "company": c2,
            "owner": demo_user,
        }
    )

    Contact.objects.get_or_create(
        email="elena.r@vanguardhealth.org",
        defaults={
            "first_name": "Elena",
            "last_name": "Rostova",
            "phone": "+1 555-0185",
            "job_title": "Chief Operations Officer",
            "company": c3,
            "owner": demo_user,
        }
    )

    # 3. Leads (5 realistic opportunities across channels & types)
    Lead.objects.get_or_create(
        name="Rahul Sharma",
        company="Acme Cloud Solutions",
        defaults={
            "email": "rahul.sharma@acmecloud.io",
            "phone": "+91 98765 43210",
            "source": "Instagram",
            "lead_type": "Organic",
            "status": "Qualified",
            "value": Decimal("350000.00"),
            "next_followup": today + timedelta(days=1),
            "notes": "Met via Instagram enterprise campaign. Evaluating CRM workflow automations.",
            "owner": demo_user,
        }
    )

    Lead.objects.get_or_create(
        name="Priya Patel",
        company="Starlight Media Group",
        defaults={
            "email": "priya.patel@starlightmedia.com",
            "phone": "+91 98765 12345",
            "source": "Google",
            "lead_type": "Organic",
            "status": "Proposal",
            "value": Decimal("720000.00"),
            "next_followup": today + timedelta(days=2),
            "notes": "Requested customized commercial proposal for 50-seat team rollout.",
            "owner": demo_user,
        }
    )

    Lead.objects.get_or_create(
        name="David Chen",
        company="Apex Robotics",
        defaults={
            "email": "david.chen@apexrobotics.co",
            "phone": "+1 555-0128",
            "source": "Website",
            "lead_type": "Organic",
            "status": "New",
            "value": Decimal("180000.00"),
            "next_followup": today + timedelta(days=3),
            "notes": "Inbound inquiry via website demo request form.",
            "owner": demo_user,
        }
    )

    Lead.objects.get_or_create(
        name="Kavita Reddy",
        company="Vanguard Health Systems",
        defaults={
            "email": "kavita.reddy@vanguardhealth.org",
            "phone": "+91 99887 76655",
            "source": "Organic",
            "lead_type": "Organic",
            "status": "Won",
            "value": Decimal("950000.00"),
            "next_followup": None,
            "notes": "Closed enterprise agreement. Transitioning account to delivery project team.",
            "owner": demo_user,
        }
    )

    Lead.objects.get_or_create(
        name="Sample Affiliate Inquiry",
        company="Promo Media Blast",
        defaults={
            "email": "blast@junklead.xyz",
            "phone": "+1 800-555-0100",
            "source": "Facebook",
            "lead_type": "Junk",
            "status": "Lost",
            "value": Decimal("0.00"),
            "next_followup": None,
            "notes": "Unsolicited promotional inquiry. Flagged as Junk for audit filtering.",
            "owner": demo_user,
        }
    )

    # 4. Projects (2 records)
    p1, _ = Project.objects.get_or_create(
        name="NEXORA Platform Migration",
        client="Acme Cloud Solutions",
        defaults={
            "description": "Enterprise cloud workflow setup and data pipeline orchestration.",
            "status": "Active",
            "budget": Decimal("500000.00"),
            "start_date": today - timedelta(days=14),
            "end_date": today + timedelta(days=60),
            "manager": demo_user,
        }
    )

    p2, _ = Project.objects.get_or_create(
        name="Digital Workflow Transformation",
        client="Starlight Media Group",
        defaults={
            "description": "Omnichannel CRM integration and custom notification automation.",
            "status": "Planning",
            "budget": Decimal("320000.00"),
            "start_date": today,
            "end_date": today + timedelta(days=90),
            "manager": demo_user,
        }
    )

    # 5. Tasks (4 action items, assigned to demo_user so they render on dashboard)
    Task.objects.get_or_create(
        title="Conduct architecture review call with Sarah Jenkins",
        assigned_to=demo_user,
        defaults={
            "due_date": today + timedelta(days=1),
            "done": False,
            "created_by": demo_user,
            "project": p1,
        }
    )

    Task.objects.get_or_create(
        title="Send revised enterprise proposal to Priya Patel",
        assigned_to=demo_user,
        defaults={
            "due_date": today + timedelta(days=2),
            "done": False,
            "created_by": demo_user,
        }
    )

    Task.objects.get_or_create(
        title="Review client onboarding checklist & milestone deliverables",
        assigned_to=demo_user,
        defaults={
            "due_date": today + timedelta(days=4),
            "done": False,
            "created_by": demo_user,
            "project": p2,
        }
    )

    Task.objects.get_or_create(
        title="Complete initial discovery and requirements scoping",
        assigned_to=demo_user,
        defaults={
            "due_date": today - timedelta(days=2),
            "done": True,
            "created_by": demo_user,
            "project": p1,
        }
    )


def get_or_create_demo_viewer():
    """
    Get or create the dedicated Demo Viewer user, ensure Demo Viewer role/permissions,
    and seed the idempotent demo dataset.
    """
    User = get_user_model()
    group = setup_demo_viewer_role()

    user, created = User.objects.get_or_create(
        email=DEMO_EMAIL,
        defaults={
            "name": DEMO_NAME,
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
        }
    )

    # Ensure clean state and role assignment
    if user.name != DEMO_NAME or not user.is_active:
        user.name = DEMO_NAME
        user.is_active = True
        user.save(update_fields=["name", "is_active"])

    user.groups.set([group])

    # Ensure dataset is present
    ensure_demo_dataset(user)

    return user

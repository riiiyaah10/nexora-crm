"""python manage.py seed --admin-email you@mail.com [--no-demo]
Creates the roles, the first admin, and (optionally) demo users + sample data."""
import os
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from accounts.models import User
from accounts.permissions import DEFAULT_ROLES, perm_objects


class Command(BaseCommand):
    help = "Create default roles, an admin user and demo data"

    def add_arguments(self, p):
        p.add_argument("--admin-email", default=os.getenv("ADMIN_EMAIL", "admin@example.com"))
        p.add_argument("--admin-name", default="Admin")
        p.add_argument("--no-demo", action="store_true")

    def handle(self, *a, **o):
        for name, codes in DEFAULT_ROLES.items():
            g, _ = Group.objects.get_or_create(name=name)
            g.permissions.set(perm_objects(codes))
        admin, _ = User.objects.get_or_create(email=o["admin_email"].lower(), defaults={"name": o["admin_name"]})
        admin.is_superuser = admin.is_staff = True
        admin.groups.set([Group.objects.get(name="Admin")])
        admin.save()
        self.stdout.write(self.style.SUCCESS(f"Admin: {admin.email}"))
        if o["no_demo"]:
            return
        demo = [("Sales User", "sales@example.com", "Sales"), ("Sales Manager", "salesmgr@example.com", "Sales Manager"),
                ("Project Manager", "pm@example.com", "Project Manager"), ("Finance User", "finance@example.com", "Finance")]
        users = {}
        for name, email, role in demo:
            u, _ = User.objects.get_or_create(email=email, defaults={"name": name})
            u.groups.set([Group.objects.get(name=role)])
            users[role] = u
        self.stdout.write(self.style.SUCCESS("Demo users: " + ", ".join(e for _, e, _ in demo)))
        from leads.models import Lead, Activity
        from projects.models import Project
        from finance.models import Invoice, Transaction
        from core.models import Task
        if Lead.objects.exists():
            return
        sales, mgr, pm = users["Sales"], users["Sales Manager"], users["Project Manager"]
        today = date.today()
        rows = [("Aarav Shah", "Zenith Travels", "Mumbai", "LinkedIn", "New", 150000, sales),
                ("Priya Mehta", "Bloom Boutique", "Ahmedabad", "Instagram", "Contacted", 80000, sales),
                ("Rohan Verma", "UrbanCart", "Delhi", "WhatsApp", "Qualified", 240000, sales),
                ("Neha Kapoor", "Trendline Retail", "Mumbai", "Email", "Proposal", 320000, mgr),
                ("Karan Joshi", "Sunrise Hotels", "Dubai", "LinkedIn", "Won", 500000, mgr),
                ("Isha Patel", "Craft & Co", "Surat", "Referral", "Lost", 60000, sales)]
        leads = []
        for n, c, city, src, st, val, owner in rows:
            l = Lead.objects.create(name=n, company=c, email=f"{n.split()[0].lower()}@example.com", phone="+91 90000 00000",
                                    source=src, status=st, value=val, owner=owner, notes=f"Based in {city}.",
                                    next_followup=today + timedelta(days=len(leads) - 1))
            Activity.objects.create(lead=l, user=owner, kind="Call", note="Intro call done, shared services deck.")
            leads.append(l)
        p1 = Project.objects.create(name="Sunrise Hotels – Brand Refresh", client="Sunrise Hotels", status="Active",
                                    budget=500000, start_date=today - timedelta(days=20), end_date=today + timedelta(days=40),
                                    manager=pm, lead=leads[4], description="Logo, social kit and website revamp.")
        p2 = Project.objects.create(name="Bloom – Instagram Campaign", client="Bloom Boutique", status="Planning",
                                    budget=120000, manager=pm)
        inv1 = Invoice.objects.create(client="Sunrise Hotels", project=p1, amount=Decimal("250000"), status="Paid",
                                      due_date=today - timedelta(days=5), paid_date=today - timedelta(days=3))
        Invoice.objects.create(client="Sunrise Hotels", project=p1, amount=Decimal("250000"), status="Sent",
                               due_date=today + timedelta(days=15))
        Invoice.objects.create(client="Bloom Boutique", project=p2, amount=Decimal("50000"), status="Sent",
                               due_date=today - timedelta(days=4))  # overdue
        Transaction.objects.create(kind="Expense", category="Software", description="Design tools", amount=12000, project=p1)
        Transaction.objects.create(kind="Expense", category="Freelancers", description="Video editor", amount=30000, project=p1)
        Transaction.objects.create(kind="Income", category="Retainer", description="Monthly retainer", amount=45000)
        Task.objects.create(title="Send proposal to Trendline", due_date=today + timedelta(days=1), assigned_to=mgr,
                            created_by=mgr, lead=leads[3])
        Task.objects.create(title="Follow up with Zenith", due_date=today, assigned_to=sales, created_by=sales, lead=leads[0])
        Task.objects.create(title="Kickoff meeting with Bloom", due_date=today + timedelta(days=3), assigned_to=pm,
                            created_by=pm, project=p2)
        self.stdout.write(self.style.SUCCESS("Sample data created."))

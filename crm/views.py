import calendar
import csv
import io
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.audit import log
from core.models import Task
from core.permissions import perm_required
from finance.models import Invoice
from leads.models import Lead, STATUSES
from projects.models import Project

from .forms import CompanyForm, ContactForm, CSVImportForm, UnifiedActivityForm
from .models import Company, Contact, INDUSTRIES, Notification, SavedFilter, Tag, UnifiedActivity

User = get_user_model()


# =========================================================
# COMPANIES
# =========================================================

@perm_required("crm.view_company")
def company_list(request):
    qs = Company.objects.select_related("owner").prefetch_related("tags", "contacts").all()
    q = request.GET.get("q", "").strip()
    industry = request.GET.get("industry", "").strip()
    tag = request.GET.get("tag", "").strip()

    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(domain__icontains=q)
            | Q(email__icontains=q)
            | Q(phone__icontains=q)
        )
    if industry:
        qs = qs.filter(industry=industry)
    if tag:
        qs = qs.filter(tags__name__iexact=tag)

    total_companies = qs.count()
    total_rev = qs.aggregate(Sum("annual_revenue"))["annual_revenue__sum"] or 0
    avg_rev = qs.aggregate(Avg("annual_revenue"))["annual_revenue__avg"] or 0

    page = Paginator(qs, 15).get_page(request.GET.get("page"))
    all_tags = Tag.objects.all()[:30]

    return render(request, "crm/companies/list.html", {
        "page": page,
        "q": q,
        "industry": industry,
        "selected_tag": tag,
        "industries": INDUSTRIES,
        "all_tags": all_tags,
        "total_companies": total_companies,
        "total_revenue": total_rev,
        "avg_revenue": avg_rev,
    })


@perm_required("crm.view_company")
def company_detail(request, pk):
    company = get_object_or_404(
        Company.objects.select_related("owner").prefetch_related("tags", "contacts", "activities__user"),
        pk=pk
    )
    # Linked leads and projects
    leads = Lead.objects.filter(Q(company__iexact=company.name) | Q(contacts__company=company)).distinct()[:10]
    projects = Project.objects.filter(client__iexact=company.name)[:10]
    invoices = Invoice.objects.filter(client__iexact=company.name).order_by("-due_date")[:10]

    activity_form = UnifiedActivityForm()

    return render(request, "crm/companies/detail.html", {
        "company": company,
        "leads": leads,
        "projects": projects,
        "invoices": invoices,
        "activity_form": activity_form,
    })


@perm_required("crm.add_company")
def company_create(request):
    form = CompanyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        company = form.save(commit=False)
        if not company.owner:
            company.owner = request.user
        company.save()
        form._save_tags(company)
        log(request.user, "create", company)
        messages.success(request, f"Company '{company.name}' created.")
        return redirect("crm:company_detail", pk=company.pk)
    return render(request, "partials/form_page.html", {
        "form": form,
        "title": "New Company Account",
        "cancel_url": reverse("crm:company_list"),
    })


@perm_required("crm.change_company")
def company_update(request, pk):
    company = get_object_or_404(Company, pk=pk)
    form = CompanyForm(request.POST or None, instance=company)
    if request.method == "POST" and form.is_valid():
        form.save()
        log(request.user, "update", company)
        messages.success(request, f"Company '{company.name}' updated.")
        return redirect("crm:company_detail", pk=company.pk)
    return render(request, "partials/form_page.html", {
        "form": form,
        "title": f"Edit {company.name}",
        "cancel_url": reverse("crm:company_detail", kwargs={"pk": company.pk}),
    })


@perm_required("crm.delete_company")
def company_delete(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == "POST":
        name = company.name
        company.delete()
        log(request.user, "delete", None, detail=f"Deleted Company {name}")
        messages.success(request, f"Company '{name}' removed.")
        return redirect("crm:company_list")
    return render(request, "partials/confirm_delete.html", {
        "title": f"Delete Company: {company.name}",
        "msg": f"Are you sure you want to delete company '{company.name}'? Contacts associated with this company will remain without an assigned company.",
        "cancel_url": reverse("crm:company_detail", kwargs={"pk": company.pk}),
    })


# =========================================================
# CONTACTS
# =========================================================

@perm_required("crm.view_contact")
def contact_list(request):
    qs = Contact.objects.select_related("company", "lead", "owner").prefetch_related("tags").all()
    q = request.GET.get("q", "").strip()
    company_id = request.GET.get("company", "").strip()
    tag = request.GET.get("tag", "").strip()

    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
            | Q(phone__icontains=q)
            | Q(job_title__icontains=q)
            | Q(company__name__icontains=q)
        )
    if company_id.isdigit():
        qs = qs.filter(company_id=int(company_id))
    if tag:
        qs = qs.filter(tags__name__iexact=tag)

    total_contacts = qs.count()
    with_company = qs.filter(company__isnull=False).count()

    page = Paginator(qs, 15).get_page(request.GET.get("page"))
    all_companies = Company.objects.all()[:40]
    all_tags = Tag.objects.all()[:30]

    return render(request, "crm/contacts/list.html", {
        "page": page,
        "q": q,
        "selected_company": company_id,
        "selected_tag": tag,
        "all_companies": all_companies,
        "all_tags": all_tags,
        "total_contacts": total_contacts,
        "with_company": with_company,
    })


@perm_required("crm.view_contact")
def contact_detail(request, pk):
    contact = get_object_or_404(
        Contact.objects.select_related("company", "lead", "owner").prefetch_related("tags", "activities__user"),
        pk=pk
    )
    activity_form = UnifiedActivityForm()
    return render(request, "crm/contacts/detail.html", {
        "contact": contact,
        "activity_form": activity_form,
    })


@perm_required("crm.add_contact")
def contact_create(request):
    company_id = request.GET.get("company")
    initial = {}
    if company_id and company_id.isdigit():
        initial["company"] = company_id

    lead_id = request.GET.get("lead")
    if lead_id and lead_id.isdigit():
        initial["lead"] = lead_id

    form = ContactForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        contact = form.save(commit=False)
        if not contact.owner:
            contact.owner = request.user
        contact.save()
        form._save_tags(contact)
        log(request.user, "create", contact)
        messages.success(request, f"Contact '{contact.full_name}' added.")
        return redirect("crm:contact_detail", pk=contact.pk)
    return render(request, "partials/form_page.html", {
        "form": form,
        "title": "New Contact",
        "cancel_url": reverse("crm:contact_list"),
    })


@perm_required("crm.change_contact")
def contact_update(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    form = ContactForm(request.POST or None, instance=contact)
    if request.method == "POST" and form.is_valid():
        form.save()
        log(request.user, "update", contact)
        messages.success(request, f"Contact '{contact.full_name}' updated.")
        return redirect("crm:contact_detail", pk=contact.pk)
    return render(request, "partials/form_page.html", {
        "form": form,
        "title": f"Edit {contact.full_name}",
        "cancel_url": reverse("crm:contact_detail", kwargs={"pk": contact.pk}),
    })


@perm_required("crm.delete_contact")
def contact_delete(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    if request.method == "POST":
        name = contact.full_name
        contact.delete()
        log(request.user, "delete", None, detail=f"Deleted Contact {name}")
        messages.success(request, f"Contact '{name}' deleted.")
        return redirect("crm:contact_list")
    return render(request, "partials/confirm_delete.html", {
        "title": f"Delete Contact: {contact.full_name}",
        "msg": f"Are you sure you want to delete contact '{contact.full_name}'?",
        "cancel_url": reverse("crm:contact_detail", kwargs={"pk": contact.pk}),
    })


# =========================================================
# UNIFIED ACTIVITY TIMELINE LOGGING
# =========================================================

@login_required
@require_POST
def activity_create(request):
    form = UnifiedActivityForm(request.POST)
    company_id = request.POST.get("company_id")
    contact_id = request.POST.get("contact_id")
    lead_id = request.POST.get("lead_id")
    project_id = request.POST.get("project_id")

    if form.is_valid():
        act = form.save(commit=False)
        act.user = request.user
        if company_id and company_id.isdigit():
            act.company_id = int(company_id)
        if contact_id and contact_id.isdigit():
            act.contact_id = int(contact_id)
        if lead_id and lead_id.isdigit():
            act.lead_id = int(lead_id)
        if project_id and project_id.isdigit():
            act.project_id = int(project_id)
        act.save()
        log(request.user, "log_activity", act, detail=f"Logged {act.kind}: {act.title}")
        messages.success(request, "Activity recorded in timeline.")
    else:
        messages.error(request, "Please enter an activity title.")

    next_url = request.POST.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("dashboard")


# =========================================================
# CRM CALENDAR
# =========================================================

@login_required
def calendar_view(request):
    today = date.today()
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
    except ValueError:
        year, month = today.year, today.month

    # Clamp month bounds
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1

    first_day = date(year, month, 1)
    num_days = calendar.monthrange(year, month)[1]
    last_day = date(year, month, num_days)

    prev_month = 12 if month == 1 else month - 1
    prev_year = year - 1 if month == 1 else year
    next_month = 1 if month == 12 else month + 1
    next_year = year + 1 if month == 12 else year

    tasks = Task.objects.filter(due_date__gte=first_day, due_date__lte=last_day).select_related("assigned_to")
    leads = Lead.objects.filter(next_followup__gte=first_day, next_followup__lte=last_day).select_related("owner")
    projects = Project.objects.filter(end_date__gte=first_day, end_date__lte=last_day).select_related("manager")
    invoices = Invoice.objects.filter(due_date__gte=first_day, due_date__lte=last_day)

    events_by_day = {d: [] for d in range(1, num_days + 1)}

    for t in tasks:
        events_by_day[t.due_date.day].append({
            "type": "task",
            "title": f"Task: {t.title}",
            "kind": "task",
            "done": t.done,
            "badge_class": "badge-emerald" if t.done else "badge-indigo",
            "url": reverse("task_toggle", kwargs={"pk": t.pk}) if t.pk else "#",
        })

    for l in leads:
        events_by_day[l.next_followup.day].append({
            "type": "followup",
            "title": f"Follow-up: {l.name} ({l.company or 'Direct'})",
            "kind": "followup",
            "badge_class": "badge-amber",
            "url": reverse("leads:detail", kwargs={"pk": l.pk}),
        })

    for p in projects:
        events_by_day[p.end_date.day].append({
            "type": "project",
            "title": f"Deadline: {p.name}",
            "kind": "project",
            "badge_class": "badge-violet",
            "url": reverse("projects:detail", kwargs={"pk": p.pk}),
        })

    for inv in invoices:
        events_by_day[inv.due_date.day].append({
            "type": "invoice",
            "title": f"Inv Due: ₹{inv.amount:,.0f} ({inv.client})",
            "kind": "invoice",
            "badge_class": "badge-rose" if inv.is_overdue else "badge-sky",
            "url": reverse("finance:invoices"),
        })

    month_cal = calendar.monthcalendar(year, month)
    calendar_weeks = []
    for week in month_cal:
        week_days = []
        for day_num in week:
            if day_num == 0:
                week_days.append({"day": 0, "events": [], "is_today": False})
            else:
                d_obj = date(year, month, day_num)
                week_days.append({
                    "day": day_num,
                    "date": d_obj,
                    "events": events_by_day.get(day_num, []),
                    "is_today": (d_obj == today),
                })
        calendar_weeks.append(week_days)

    return render(request, "crm/calendar.html", {
        "calendar_weeks": calendar_weeks,
        "current_month_name": calendar.month_name[month],
        "current_year": year,
        "current_month": month,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "today": today,
        "total_events_month": len(tasks) + len(leads) + len(projects) + len(invoices),
    })


# =========================================================
# REPORTS & ANALYTICS
# =========================================================

@perm_required("crm.view_reports")
def reports_view(request):
    total_leads = Lead.objects.count()

    stage_counts = {s: 0 for s in STATUSES}
    for item in Lead.objects.values("status").annotate(count=Count("id")):
        stage_counts[item["status"]] = item["count"]

    funnel = []
    for s in STATUSES:
        cnt = stage_counts.get(s, 0)
        pct = (cnt / total_leads * 100) if total_leads > 0 else 0
        funnel.append({
            "status": s,
            "label": s,
            "count": cnt,
            "percentage": round(pct, 1),
        })

    won_count = stage_counts.get("Won", 0)
    lost_count = stage_counts.get("Lost", 0)
    closed = won_count + lost_count
    win_rate = round((won_count / closed * 100), 1) if closed > 0 else 0

    won_revenue = Lead.objects.filter(status="Won").aggregate(Sum("value"))["value__sum"] or 0
    pipeline_revenue = Lead.objects.exclude(status__in=["Won", "Lost"]).aggregate(Sum("value"))["value__sum"] or 0

    source_stats = (
        Lead.objects.values("source")
        .annotate(total=Count("id"), won=Count("id", filter=Q(status="Won")), val=Sum("value"))
        .order_by("-total")[:8]
    )

    rep_stats = (
        User.objects.annotate(
            assigned_leads=Count("leads", distinct=True),
            won_deals=Count("leads", filter=Q(leads__status="Won"), distinct=True),
            won_value=Sum("leads__value", filter=Q(leads__status="Won")),
            open_tasks=Count("tasks", filter=Q(tasks__done=False), distinct=True),
        )
        .filter(assigned_leads__gt=0)
        .order_by("-won_value")[:10]
    )

    paid_sum = Invoice.objects.filter(status="Paid").aggregate(Sum("amount"))["amount__sum"] or 0
    pending_sum = Invoice.objects.filter(status="Sent").aggregate(Sum("amount"))["amount__sum"] or 0
    today = date.today()
    overdue_sum = Invoice.objects.filter(status="Sent", due_date__lt=today).aggregate(Sum("amount"))["amount__sum"] or 0

    return render(request, "crm/reports.html", {
        "funnel": funnel,
        "total_leads": total_leads,
        "win_rate": win_rate,
        "won_count": won_count,
        "lost_count": lost_count,
        "won_revenue": won_revenue,
        "pipeline_revenue": pipeline_revenue,
        "source_stats": source_stats,
        "rep_stats": rep_stats,
        "paid_sum": paid_sum,
        "pending_sum": pending_sum,
        "overdue_sum": overdue_sum,
    })


# =========================================================
# GLOBAL OMNISEARCH API & VIEW
# =========================================================

@login_required
def api_search(request):
    q = request.GET.get("q", "").strip()
    if not q or len(q) < 2:
        return JsonResponse({"results": []})

    results = []

    # 1. Leads
    leads = Lead.objects.filter(
        Q(name__icontains=q) | Q(company__icontains=q) | Q(email__icontains=q)
    )[:5]
    if leads.exists():
        results.append({
            "category": "Leads",
            "items": [
                {
                    "title": l.name,
                    "subtitle": f"{l.company or 'Direct'} · ₹{l.value:,.0f} · {l.status}",
                    "url": reverse("leads:detail", kwargs={"pk": l.pk}),
                }
                for l in leads
            ]
        })

    # 2. Contacts
    contacts = Contact.objects.filter(
        Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q) | Q(job_title__icontains=q)
    ).select_related("company")[:5]
    if contacts.exists():
        results.append({
            "category": "Contacts",
            "items": [
                {
                    "title": c.full_name,
                    "subtitle": f"{c.job_title or 'Contact'}{' @ ' + c.company.name if c.company else ''}",
                    "url": reverse("crm:contact_detail", kwargs={"pk": c.pk}),
                }
                for c in contacts
            ]
        })

    # 3. Companies
    companies = Company.objects.filter(
        Q(name__icontains=q) | Q(domain__icontains=q) | Q(industry__icontains=q)
    )[:5]
    if companies.exists():
        results.append({
            "category": "Companies",
            "items": [
                {
                    "title": cmp.name,
                    "subtitle": f"{cmp.industry or 'Business'} · ₹{cmp.annual_revenue:,.0f}",
                    "url": reverse("crm:company_detail", kwargs={"pk": cmp.pk}),
                }
                for cmp in companies
            ]
        })

    # 4. Projects
    projects = Project.objects.filter(
        Q(name__icontains=q) | Q(client__icontains=q)
    )[:5]
    if projects.exists():
        results.append({
            "category": "Projects",
            "items": [
                {
                    "title": p.name,
                    "subtitle": f"Client: {p.client} · Status: {p.status}",
                    "url": reverse("projects:detail", kwargs={"pk": p.pk}),
                }
                for p in projects
            ]
        })

    # 5. Invoices
    invoices = Invoice.objects.filter(
        Q(client__icontains=q) | Q(status__icontains=q)
    )[:5]
    if invoices.exists():
        results.append({
            "category": "Invoices",
            "items": [
                {
                    "title": f"Invoice #{inv.pk} · {inv.client}",
                    "subtitle": f"₹{inv.amount:,.0f} · {inv.status} (Due {inv.due_date})",
                    "url": reverse("finance:invoices"),
                }
                for inv in invoices
            ]
        })

    return JsonResponse({"results": results})


@login_required
def search_view(request):
    q = request.GET.get("q", "").strip()
    leads = Lead.objects.filter(Q(name__icontains=q) | Q(company__icontains=q) | Q(email__icontains=q))[:15] if q else []
    contacts = Contact.objects.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))[:15] if q else []
    companies = Company.objects.filter(Q(name__icontains=q) | Q(domain__icontains=q))[:15] if q else []
    projects = Project.objects.filter(Q(name__icontains=q) | Q(client__icontains=q))[:15] if q else []

    total_results = len(leads) + len(contacts) + len(companies) + len(projects)

    return render(request, "crm/search.html", {
        "q": q,
        "leads": leads,
        "contacts": contacts,
        "companies": companies,
        "projects": projects,
        "total_results": total_results,
    })


# =========================================================
# NOTIFICATION CENTER
# =========================================================

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by("-id")
    unread_count = notifications.filter(read=False).count()
    page = Paginator(notifications, 20).get_page(request.GET.get("page"))

    return render(request, "crm/notifications.html", {
        "page": page,
        "unread_count": unread_count,
    })


@login_required
def notification_mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.read = True
    notif.save()
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"status": "ok"})
    if notif.link:
        return redirect(notif.link)
    return redirect("crm:notifications")


@login_required
@require_POST
def notification_read_all(request):
    Notification.objects.filter(user=request.user, read=False).update(read=True)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"status": "ok"})
    messages.success(request, "All notifications marked as read.")
    return redirect("crm:notifications")


# =========================================================
# CSV IMPORT & EXPORT
# =========================================================

@login_required
def import_csv(request):
    if request.method == "POST":
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            target = form.cleaned_data["target"]
            csv_file = request.FILES["file"]

            try:
                decoded_file = csv_file.read().decode("utf-8-sig")
                io_string = io.StringIO(decoded_file)
                reader = csv.DictReader(io_string)

                created_count = 0
                error_rows = []

                if target == "leads":
                    if not request.user.has_perm("leads.add_lead"):
                        messages.error(request, "Permission denied to add leads.")
                        return redirect("crm:import_csv")

                    for idx, row in enumerate(reader, start=2):
                        name = row.get("name", "").strip() or row.get("Name", "").strip()
                        if not name:
                            error_rows.append(f"Row {idx}: Name is required")
                            continue
                        company = row.get("company", "").strip() or row.get("Company", "").strip()
                        email = row.get("email", "").strip() or row.get("Email", "").strip()
                        phone = row.get("phone", "").strip() or row.get("Phone", "").strip()
                        status = row.get("status", "").strip() or row.get("Status", "").strip() or "New"
                        source = row.get("source", "").strip() or row.get("Source", "").strip() or "Website"
                        try:
                            raw_val = row.get("value", "0").replace(",", "").strip()
                            value = Decimal(raw_val or "0")
                        except Exception:
                            value = Decimal("0")

                        Lead.objects.create(
                            name=name,
                            company=company,
                            email=email,
                            phone=phone,
                            status=status if status in STATUSES else "New",
                            source=source,
                            value=value,
                            owner=request.user,
                        )
                        created_count += 1

                elif target == "contacts":
                    if not request.user.has_perm("crm.add_contact"):
                        messages.error(request, "Permission denied to add contacts.")
                        return redirect("crm:import_csv")

                    for idx, row in enumerate(reader, start=2):
                        first_name = row.get("first_name", "").strip() or row.get("First Name", "").strip()
                        if not first_name:
                            error_rows.append(f"Row {idx}: First Name is required")
                            continue
                        last_name = row.get("last_name", "").strip() or row.get("Last Name", "").strip()
                        email = row.get("email", "").strip() or row.get("Email", "").strip()
                        phone = row.get("phone", "").strip() or row.get("Phone", "").strip()
                        job_title = row.get("job_title", "").strip() or row.get("Job Title", "").strip()
                        comp_name = row.get("company", "").strip() or row.get("Company", "").strip()

                        company_obj = None
                        if comp_name:
                            company_obj, _ = Company.objects.get_or_create(
                                name=comp_name,
                                defaults={"owner": request.user}
                            )

                        Contact.objects.create(
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            phone=phone,
                            job_title=job_title,
                            company=company_obj,
                            owner=request.user,
                        )
                        created_count += 1

                elif target == "companies":
                    if not request.user.has_perm("crm.add_company"):
                        messages.error(request, "Permission denied to add companies.")
                        return redirect("crm:import_csv")

                    for idx, row in enumerate(reader, start=2):
                        name = row.get("name", "").strip() or row.get("Name", "").strip()
                        if not name:
                            error_rows.append(f"Row {idx}: Company Name is required")
                            continue
                        domain = row.get("domain", "").strip() or row.get("Domain", "").strip()
                        industry = row.get("industry", "").strip() or row.get("Industry", "").strip()
                        website = row.get("website", "").strip() or row.get("Website", "").strip()
                        phone = row.get("phone", "").strip() or row.get("Phone", "").strip()

                        Company.objects.get_or_create(
                            name=name,
                            defaults={
                                "domain": domain,
                                "industry": industry,
                                "website": website,
                                "phone": phone,
                                "owner": request.user,
                            }
                        )
                        created_count += 1

                log(request.user, "csv_import", None, detail=f"Imported {created_count} {target}")
                messages.success(request, f"Successfully imported {created_count} {target} records.")
                if error_rows:
                    messages.warning(request, f"Some rows failed: {', '.join(error_rows[:5])}")

                if target == "contacts":
                    return redirect("crm:contact_list")
                elif target == "companies":
                    return redirect("crm:company_list")
                else:
                    return redirect("leads:list")

            except Exception as e:
                messages.error(request, f"Failed to process CSV: {str(e)}")
    else:
        form = CSVImportForm()

    return render(request, "crm/import.html", {"form": form})


@login_required
def export_contacts_csv(request):
    if not request.user.has_perm("crm.view_contact"):
        messages.error(request, "Permission denied.")
        return redirect("crm:contact_list")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="contacts_export.csv"'
    writer = csv.writer(response)
    writer.writerow(["First Name", "Last Name", "Email", "Phone", "Job Title", "Company", "Owner", "Created At"])

    contacts = Contact.objects.select_related("company", "owner").all()
    for c in contacts:
        writer.writerow([
            c.first_name,
            c.last_name,
            c.email,
            c.phone,
            c.job_title,
            c.company.name if c.company else "",
            c.owner.email if c.owner else "",
            c.created_at.strftime("%Y-%m-%d %H:%M"),
        ])
    return response


@login_required
def export_companies_csv(request):
    if not request.user.has_perm("crm.view_company"):
        messages.error(request, "Permission denied.")
        return redirect("crm:company_list")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="companies_export.csv"'
    writer = csv.writer(response)
    writer.writerow(["Name", "Domain", "Industry", "Website", "Phone", "Email", "Annual Revenue", "Owner", "Created At"])

    companies = Company.objects.select_related("owner").all()
    for cmp in companies:
        writer.writerow([
            cmp.name,
            cmp.domain,
            cmp.industry,
            cmp.website,
            cmp.phone,
            cmp.email,
            f"{cmp.annual_revenue:.2f}",
            cmp.owner.email if cmp.owner else "",
            cmp.created_at.strftime("%Y-%m-%d %H:%M"),
        ])
    return response

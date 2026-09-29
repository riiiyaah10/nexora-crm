import csv
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.audit import log
from core.forms import TaskForm
from core.permissions import perm_required
from projects.models import Project
from .forms import LeadForm, ActivityForm
from .models import Lead, Activity, STATUSES
from .services import visible_leads


def _filtered(request):
    qs = visible_leads(request.user)
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(company__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q))
    if status in STATUSES:
        qs = qs.filter(status=status)
    return qs, q, status


@perm_required("leads.view_lead")
def lead_list(request):
    qs, q, status = _filtered(request)
    view = request.GET.get("view", "table")
    ctx = {"q": q, "status": status, "statuses": STATUSES, "view": view}
    if view == "board":
        items = list(qs[:400])
        ctx["columns"] = [(s, [l for l in items if l.status == s]) for s in STATUSES]
    else:
        ctx["page"] = Paginator(qs, 10).get_page(request.GET.get("page"))
    return render(request, "leads/list.html", ctx)


@perm_required("leads.add_lead")
def lead_create(request):
    form = LeadForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        lead = form.save(commit=False)
        lead.owner = lead.owner or request.user
        lead.save()
        log(request.user, "create", lead)
        messages.success(request, "Lead added.")
        return redirect("leads:detail", pk=lead.pk)
    return render(request, "partials/form_page.html", {"form": form, "title": "New lead", "cancel_url": reverse("leads:list")})


@perm_required("leads.view_lead")
def lead_detail(request, pk):
    lead = get_object_or_404(visible_leads(request.user), pk=pk)
    return render(request, "leads/detail.html", {
        "lead": lead, "activities": lead.activities.select_related("user"), "tasks": lead.tasks.select_related("assigned_to"),
        "activity_form": ActivityForm(), "task_form": TaskForm(), "statuses": STATUSES,
        "can_convert": request.user.has_perm("leads.change_lead") and request.user.has_perm("projects.add_project"),
        "converted": Project.objects.filter(lead=lead).first()})


@perm_required("leads.change_lead")
def lead_update(request, pk):
    lead = get_object_or_404(visible_leads(request.user), pk=pk)
    form = LeadForm(request.POST or None, instance=lead, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        log(request.user, "update", lead)
        messages.success(request, "Lead updated.")
        return redirect("leads:detail", pk=pk)
    return render(request, "partials/form_page.html", {"form": form, "title": f"Edit {lead.name}",
                                                       "cancel_url": reverse("leads:detail", args=[pk])})


@perm_required("leads.delete_lead")
def lead_delete(request, pk):
    lead = get_object_or_404(visible_leads(request.user), pk=pk)
    if request.method == "POST":
        log(request.user, "delete", lead)
        lead.delete()
        messages.success(request, "Lead deleted.")
        return redirect("leads:list")
    return render(request, "partials/confirm_delete.html", {"object": lead, "cancel_url": reverse("leads:detail", args=[pk])})


@require_POST
@perm_required("leads.change_lead")
def lead_status(request, pk):
    lead = get_object_or_404(visible_leads(request.user), pk=pk)
    if request.POST.get("status") in STATUSES:
        lead.status = request.POST["status"]
        lead.save(update_fields=["status", "updated_at"])
        log(request.user, "status", lead, f"{lead.name} → {lead.status}")
    return redirect(request.POST.get("next") or "leads:list")


@require_POST
@perm_required("leads.change_lead")
def lead_activity(request, pk):
    lead = get_object_or_404(visible_leads(request.user), pk=pk)
    form = ActivityForm(request.POST)
    if form.is_valid():
        a = form.save(commit=False)
        a.lead, a.user = lead, request.user
        a.save()
    return redirect("leads:detail", pk=pk)


@require_POST
@perm_required("leads.change_lead", "projects.add_project")
def lead_convert(request, pk):
    lead = get_object_or_404(visible_leads(request.user), pk=pk)
    project = Project.objects.filter(lead=lead).first()
    if not project:
        project = Project.objects.create(name=f"{lead.company or lead.name} – Project", client=lead.company or lead.name,
                                         budget=lead.value, lead=lead, manager=request.user)
        lead.status = "Won"
        lead.save(update_fields=["status", "updated_at"])
        Activity.objects.create(lead=lead, user=request.user, kind="Note", note="Converted to project.")
        log(request.user, "convert", lead, f"→ project #{project.pk}")
        messages.success(request, "Lead marked Won and a project was created.")
    if request.user.has_perm("projects.view_project"):
        return redirect("projects:detail", pk=project.pk)
    return redirect("leads:detail", pk=pk)


@perm_required("leads.view_lead")
def lead_export(request):
    qs, _, _ = _filtered(request)
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="leads.csv"'
    w = csv.writer(resp)
    w.writerow(["Name", "Company", "Email", "Phone", "Source", "Status", "Value", "Next follow-up", "Owner", "Created"])
    for l in qs:
        w.writerow([l.name, l.company, l.email, l.phone, l.source, l.status, l.value, l.next_followup or "",
                    l.owner or "", l.created_at.date()])
    return resp

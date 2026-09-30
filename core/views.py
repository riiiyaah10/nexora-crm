from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from leads.models import STATUSES as LEAD_STATUSES
from leads.services import visible_leads
from projects.models import Project, STATUSES as PROJECT_STATUSES
from .forms import TaskForm
from .models import Task
from .permissions import perm_required

from leads.models import Lead
from accounts.models import User

HOME_ORDER = [("core.view_dashboard", "dashboard"), ("leads.view_lead", "leads:list"),
              ("projects.view_project", "projects:list"), ("finance.view_finance", "finance:overview"),
              ("accounts.manage_users", "accounts:users")]


def home(request):
    """Send each user to the first area they are allowed to see."""
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    for perm, url in HOME_ORDER:
        if request.user.has_perm(perm):
            return redirect(url)
    raise PermissionDenied

@perm_required("core.view_dashboard")
def dashboard(request):
    u, ctx = request.user, {}

    # -------------------------
    # LEADS
    # -------------------------
    if u.has_perm("leads.view_lead"):
        qs = visible_leads(u)

        counts = {
            r["status"]: r["n"]
            for r in qs.values("status").annotate(n=Count("id"))
        }

        top = max(list(counts.values()) + [1])

        ctx["pipeline"] = [
            (
                s,
                counts.get(s, 0),
                int(counts.get(s, 0) / top * 100)
            )
            for s in LEAD_STATUSES
        ]

        values = {
            r["status"]: r["v"] or 0
            for r in qs.values("status").annotate(v=Sum("value"))
        }

        total_leads = qs.count()

        ctx["pipe_distribution"] = [
            (
                s,
                counts.get(s, 0),
                int(counts.get(s, 0) / total_leads * 100) if total_leads > 0 else 0,
                values.get(s, 0)
            )
            for s in LEAD_STATUSES
        ]

        ctx["leads_total"] = total_leads
        ctx["leads_new"] = counts.get("New", 0)

        ctx["won_value"] = (
            qs.filter(status="Won")
            .aggregate(v=Sum("value"))["v"] or 0
        )

        ctx["followups"] = (
            qs.exclude(status__in=["Won", "Lost"])
            .filter(next_followup__lte=timezone.localdate())
            .order_by("next_followup")[:6]
        )

        # Leads available for task assignment
        ctx["leads"] = qs

    # -------------------------
    # PROJECTS
    # -------------------------
    if u.has_perm("projects.view_project"):
        pc = {
            r["status"]: r["n"]
            for r in Project.objects
            .values("status")
            .annotate(n=Count("id"))
        }

        ctx["project_counts"] = [
            (s, pc.get(s, 0))
            for s in PROJECT_STATUSES
        ]

        ctx["projects_total"] = sum(pc.values())

        # Projects available for task assignment
        ctx["projects"] = Project.objects.all()

    # -------------------------
    # FINANCE
    # -------------------------
    if u.has_perm("finance.view_finance"):
        from finance.services import summary
        ctx["fin"] = summary()

    # -------------------------
    # EMPLOYEES
    # -------------------------
    ctx["users"] = User.objects.filter(
        is_active=True
    ).order_by("name")

    # -------------------------
    # MY OPEN TASKS
    # -------------------------
    ctx["my_tasks"] = (
        Task.objects
        .filter(
            assigned_to=u,
            done=False
        )
        .select_related("lead", "project")
        .order_by(
            F("due_date").asc(nulls_last=True)
        )[:8]
    )

    return render(
        request,
        "core/dashboard.html",
        ctx
    )

def _back(request, default="home"):
    nxt = request.POST.get("next", "")
    return redirect(nxt if url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}) else default)


@require_POST
@perm_required()
def task_create(request):
    form = TaskForm(request.POST)

    if form.is_valid():

        lead = form.cleaned_data["lead"]
        project = form.cleaned_data["project"]

        if lead:
            if not request.user.has_perm("leads.view_lead"):
                raise PermissionDenied

            if not visible_leads(request.user).filter(
                pk=lead.pk
            ).exists():
                raise PermissionDenied

        if project:
            if not request.user.has_perm("projects.view_project"):
                raise PermissionDenied

        Task.objects.create(
            title=form.cleaned_data["title"],
            due_date=form.cleaned_data["due_date"],
            assigned_to=form.cleaned_data["assigned_to"],
            created_by=request.user,
            lead=lead,
            project=project,
        )

        messages.success(
            request,
            "Task created successfully."
        )

    else:
        messages.error(
            request,
            "Please enter a valid task."
        )

    return _back(request)

@require_POST
@perm_required()
def task_toggle(request, pk):
    t = get_object_or_404(Task, pk=pk)
    if request.user.pk not in (t.assigned_to_id, t.created_by_id):
        raise PermissionDenied
    t.done = not t.done
    t.save(update_fields=["done"])
    return _back(request)


@require_POST
@perm_required()
def task_delete(request, pk):
    t = get_object_or_404(Task, pk=pk)
    if request.user.pk not in (t.assigned_to_id, t.created_by_id):
        raise PermissionDenied
    t.delete()
    return _back(request)

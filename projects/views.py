from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.audit import log
from core.forms import TaskForm
from core.permissions import perm_required
from .forms import ProjectForm
from .models import Project, STATUSES


@perm_required("projects.view_project")
def project_list(request):
    qs = Project.objects.select_related("manager")
    q, status = request.GET.get("q", "").strip(), request.GET.get("status", "")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(client__icontains=q))
    if status in STATUSES:
        qs = qs.filter(status=status)
    page = Paginator(qs, 10).get_page(request.GET.get("page"))
    return render(request, "projects/list.html", {"page": page, "q": q, "status": status, "statuses": STATUSES})


@perm_required("projects.add_project")
def project_create(request):
    form = ProjectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        p = form.save()
        log(request.user, "create", p)
        messages.success(request, "Project created.")
        return redirect("projects:detail", pk=p.pk)
    return render(request, "partials/form_page.html", {"form": form, "title": "New project", "cancel_url": reverse("projects:list")})


@perm_required("projects.view_project")
def project_detail(request, pk):
    p = get_object_or_404(Project.objects.select_related("manager", "lead"), pk=pk)
    ctx = {"project": p, "tasks": p.tasks.select_related("assigned_to"), "task_form": TaskForm(), "statuses": STATUSES}
    if request.user.has_perm("finance.view_finance"):  # finance numbers only for people allowed to see finance
        from finance.services import project_finance
        ctx["fin"] = project_finance(p)
    if p.lead_id and request.user.has_perm("leads.view_lead"):
        ctx["show_lead"] = True
    return render(request, "projects/detail.html", ctx)


@perm_required("projects.change_project")
def project_update(request, pk):
    p = get_object_or_404(Project, pk=pk)
    form = ProjectForm(request.POST or None, instance=p)
    if request.method == "POST" and form.is_valid():
        form.save()
        log(request.user, "update", p)
        messages.success(request, "Project updated.")
        return redirect("projects:detail", pk=pk)
    return render(request, "partials/form_page.html", {"form": form, "title": f"Edit {p.name}",
                                                       "cancel_url": reverse("projects:detail", args=[pk])})


@perm_required("projects.delete_project")
def project_delete(request, pk):
    p = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        log(request.user, "delete", p)
        p.delete()
        messages.success(request, "Project deleted.")
        return redirect("projects:list")
    return render(request, "partials/confirm_delete.html", {"object": p, "cancel_url": reverse("projects:detail", args=[pk])})


@require_POST
@perm_required("projects.change_project")
def project_status(request, pk):
    p = get_object_or_404(Project, pk=pk)
    if request.POST.get("status") in STATUSES:
        p.status = request.POST["status"]
        p.save(update_fields=["status"])
        log(request.user, "status", p, f"{p.name} → {p.status}")
    return redirect("projects:detail", pk=pk)

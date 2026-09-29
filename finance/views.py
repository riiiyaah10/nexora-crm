from datetime import date
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.audit import log
from core.permissions import perm_required
from .forms import InvoiceForm, TransactionForm
from .models import Invoice, Transaction
from .services import summary


@perm_required("finance.view_finance")
def overview(request):
    return render(request, "finance/overview.html", {
        "s": summary(), "recent": Invoice.objects.select_related("project")[:5]})


@perm_required("finance.view_finance")
def invoice_list(request):
    qs = Invoice.objects.select_related("project")
    status = request.GET.get("status", "")
    if status:
        qs = [i for i in qs if i.effective_status == status]
    page = Paginator(qs, 12).get_page(request.GET.get("page"))
    return render(request, "finance/invoices.html", {"page": page, "status": status,
                                                    "statuses": ["Draft", "Sent", "Overdue", "Paid"]})


@perm_required("finance.add_invoice")
def invoice_create(request):
    form = InvoiceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        inv = form.save()
        log(request.user, "create", inv)
        messages.success(request, f"Invoice {inv.number} created.")
        return redirect("finance:invoices")
    return render(request, "partials/form_page.html", {"form": form, "title": "New invoice", "cancel_url": reverse("finance:invoices")})


@perm_required("finance.change_invoice")
def invoice_update(request, pk):
    inv = get_object_or_404(Invoice, pk=pk)
    form = InvoiceForm(request.POST or None, instance=inv)
    if request.method == "POST" and form.is_valid():
        inv = form.save()
        if inv.status == "Paid" and not inv.paid_date:
            inv.paid_date = date.today()
            inv.save(update_fields=["paid_date"])
        log(request.user, "update", inv)
        return redirect("finance:invoices")
    return render(request, "partials/form_page.html", {"form": form, "title": f"Edit {inv.number}", "cancel_url": reverse("finance:invoices")})


@require_POST
@perm_required("finance.change_invoice")
def invoice_status(request, pk):
    inv = get_object_or_404(Invoice, pk=pk)
    new = request.POST.get("status")
    if new in ("Draft", "Sent", "Paid"):
        inv.status = new
        inv.paid_date = date.today() if new == "Paid" else None
        inv.save()
        log(request.user, "status", inv, f"{inv.number} → {new}")
    return redirect("finance:invoices")


@perm_required("finance.delete_invoice")
def invoice_delete(request, pk):
    inv = get_object_or_404(Invoice, pk=pk)
    if request.method == "POST":
        log(request.user, "delete", inv)
        inv.delete()
        return redirect("finance:invoices")
    return render(request, "partials/confirm_delete.html", {"object": inv, "cancel_url": reverse("finance:invoices")})


@perm_required("finance.view_finance")
def transaction_list(request):
    qs = Transaction.objects.select_related("project")
    kind = request.GET.get("kind", "")
    if kind in ("Income", "Expense"):
        qs = qs.filter(kind=kind)
    page = Paginator(qs, 12).get_page(request.GET.get("page"))
    return render(request, "finance/transactions.html", {"page": page, "kind": kind})


@perm_required("finance.add_transaction")
def transaction_create(request):
    form = TransactionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        t = form.save()
        log(request.user, "create", t, f"{t.kind} ₹{t.amount}")
        messages.success(request, "Entry added.")
        return redirect("finance:transactions")
    return render(request, "partials/form_page.html", {"form": form, "title": "New income / expense", "cancel_url": reverse("finance:transactions")})


@perm_required("finance.delete_transaction")
def transaction_delete(request, pk):
    t = get_object_or_404(Transaction, pk=pk)
    if request.method == "POST":
        log(request.user, "delete", t, f"{t.kind} ₹{t.amount}")
        t.delete()
        return redirect("finance:transactions")
    return render(request, "partials/confirm_delete.html", {"object": f"{t.kind}: ₹{t.amount}", "cancel_url": reverse("finance:transactions")})

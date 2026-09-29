from datetime import date
from decimal import Decimal
from .models import Invoice, Transaction

ZERO = Decimal("0")


def _month_keys(n=6):
    y, m = date.today().year, date.today().month
    keys = []
    for _ in range(n):
        keys.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(keys))


def summary():
    invoices, tx = list(Invoice.objects.all()), list(Transaction.objects.all())
    paid = sum((i.total for i in invoices if i.status == "Paid"), ZERO)
    outstanding = sum((i.total for i in invoices if i.status == "Sent"), ZERO)
    overdue = sum((i.total for i in invoices if i.effective_status == "Overdue"), ZERO)
    income = paid + sum((t.amount for t in tx if t.kind == "Income"), ZERO)
    expense = sum((t.amount for t in tx if t.kind == "Expense"), ZERO)
    months = []
    for y, m in _month_keys():
        inc = sum((i.total for i in invoices if i.status == "Paid" and (i.paid_date or i.issue_date).year == y
                   and (i.paid_date or i.issue_date).month == m), ZERO)
        inc += sum((t.amount for t in tx if t.kind == "Income" and t.date.year == y and t.date.month == m), ZERO)
        exp = sum((t.amount for t in tx if t.kind == "Expense" and t.date.year == y and t.date.month == m), ZERO)
        months.append({"label": date(y, m, 1).strftime("%b %y"), "income": inc, "expense": exp})
    top = max([max(x["income"], x["expense"]) for x in months] + [Decimal("1")])
    for x in months:
        x["income_pct"] = int(x["income"] / top * 100)
        x["expense_pct"] = int(x["expense"] / top * 100)
    return {"income": income, "expense": expense, "net": income - expense, "outstanding": outstanding,
            "overdue": overdue, "months": months}


def project_finance(project):
    inv = list(project.invoices.all())
    billed = sum((i.total for i in inv), ZERO)
    paid = sum((i.total for i in inv if i.status == "Paid"), ZERO)
    spent = sum((t.amount for t in project.transactions.filter(kind="Expense")), ZERO)
    return {"billed": billed, "paid": paid, "spent": spent, "profit": paid - spent, "invoices": inv}

from datetime import date
from decimal import Decimal
from django.db import models

INVOICE_STATUSES = ["Draft", "Sent", "Paid"]


class Invoice(models.Model):
    number = models.CharField(max_length=20, unique=True, blank=True)
    client = models.CharField(max_length=120)
    project = models.ForeignKey("projects.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices")
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Amount before tax")
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18, verbose_name="GST / tax %")
    status = models.CharField(max_length=10, choices=[(s, s) for s in INVOICE_STATUSES], default="Draft")
    issue_date = models.DateField(default=date.today)
    due_date = models.DateField(null=True, blank=True)
    paid_date = models.DateField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-id"]
        permissions = [("view_finance", "Can view the finance module")]

    def save(self, *a, **kw):
        super().save(*a, **kw)
        if not self.number:
            self.number = f"INV-{self.pk:04d}"
            super().save(update_fields=["number"])

    @property
    def total(self):
        return (self.amount * (Decimal(1) + self.tax_percent / Decimal(100))).quantize(Decimal("0.01"))

    @property
    def effective_status(self):
        if self.status == "Sent" and self.due_date and self.due_date < date.today():
            return "Overdue"
        return self.status

    def __str__(self):
        return f"{self.number} – {self.client}"


class Transaction(models.Model):
    KINDS = [("Income", "Income"), ("Expense", "Expense")]
    kind = models.CharField(max_length=10, choices=KINDS)
    category = models.CharField(max_length=50, blank=True)
    description = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=date.today)
    project = models.ForeignKey("projects.Project", null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="transactions")

    class Meta:
        ordering = ["-date", "-id"]

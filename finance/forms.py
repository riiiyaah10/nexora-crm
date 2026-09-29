from django import forms
from core.forms import StyledFormMixin, date_widget
from .models import Invoice, Transaction


class InvoiceForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["client", "project", "amount", "tax_percent", "status", "issue_date", "due_date", "notes"]
        widgets = {"issue_date": date_widget(), "due_date": date_widget()}


class TransactionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["kind", "category", "description", "amount", "date", "project"]
        widgets = {"date": date_widget()}

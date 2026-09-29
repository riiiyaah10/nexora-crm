from django import forms
from django.contrib.auth import get_user_model
from .models import Company, Contact, UnifiedActivity, Tag, SavedFilter

User = get_user_model()


class CompanyForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        label="Tags (comma-separated)",
        widget=forms.TextInput(attrs={"placeholder": "Enterprise, VIP, SaaS", "class": "crm-input"})
    )

    class Meta:
        model = Company
        fields = [
            "name",
            "domain",
            "industry",
            "website",
            "phone",
            "email",
            "annual_revenue",
            "employee_count",
            "address",
            "owner",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "crm-input", "placeholder": "Acme Global Corp"}),
            "domain": forms.TextInput(attrs={"class": "crm-input", "placeholder": "acmeglobal.com"}),
            "industry": forms.Select(attrs={"class": "crm-select"}),
            "website": forms.URLInput(attrs={"class": "crm-input", "placeholder": "https://acmeglobal.com"}),
            "phone": forms.TextInput(attrs={"class": "crm-input", "placeholder": "+91 98765 43210"}),
            "email": forms.EmailInput(attrs={"class": "crm-input", "placeholder": "contact@acmeglobal.com"}),
            "annual_revenue": forms.NumberInput(attrs={"class": "crm-input", "placeholder": "0.00", "step": "1000"}),
            "employee_count": forms.NumberInput(attrs={"class": "crm-input", "placeholder": "50"}),
            "address": forms.Textarea(attrs={"class": "crm-textarea", "rows": 3, "placeholder": "HQ Address, City, Country"}),
            "owner": forms.Select(attrs={"class": "crm-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["tags_input"].initial = ", ".join(t.name for t in self.instance.tags.all())

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            self._save_tags(instance)
        return instance

    def _save_tags(self, instance):
        raw_tags = self.cleaned_data.get("tags_input", "")
        tag_names = [t.strip() for t in raw_tags.split(",") if t.strip()]
        tag_objects = []
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(name=name)
            tag_objects.append(tag)
        instance.tags.set(tag_objects)


class ContactForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        label="Tags (comma-separated)",
        widget=forms.TextInput(attrs={"placeholder": "Decision Maker, Technical, Champion", "class": "crm-input"})
    )

    class Meta:
        model = Contact
        fields = [
            "first_name",
            "last_name",
            "job_title",
            "company",
            "email",
            "phone",
            "lead",
            "owner",
            "notes",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "crm-input", "placeholder": "John"}),
            "last_name": forms.TextInput(attrs={"class": "crm-input", "placeholder": "Doe"}),
            "job_title": forms.TextInput(attrs={"class": "crm-input", "placeholder": "Chief Technology Officer"}),
            "company": forms.Select(attrs={"class": "crm-select"}),
            "email": forms.EmailInput(attrs={"class": "crm-input", "placeholder": "john.doe@company.com"}),
            "phone": forms.TextInput(attrs={"class": "crm-input", "placeholder": "+91 98765 43210"}),
            "lead": forms.Select(attrs={"class": "crm-select"}),
            "owner": forms.Select(attrs={"class": "crm-select"}),
            "notes": forms.Textarea(attrs={"class": "crm-textarea", "rows": 3, "placeholder": "Executive background, preferences, meeting context..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["tags_input"].initial = ", ".join(t.name for t in self.instance.tags.all())

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            self._save_tags(instance)
        return instance

    def _save_tags(self, instance):
        raw_tags = self.cleaned_data.get("tags_input", "")
        tag_names = [t.strip() for t in raw_tags.split(",") if t.strip()]
        tag_objects = []
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(name=name)
            tag_objects.append(tag)
        instance.tags.set(tag_objects)


class UnifiedActivityForm(forms.ModelForm):
    class Meta:
        model = UnifiedActivity
        fields = ["kind", "title", "note"]
        widgets = {
            "kind": forms.Select(attrs={"class": "crm-select"}),
            "title": forms.TextInput(attrs={"class": "crm-input", "placeholder": "Call summary, Demo feedback, Next steps..."}),
            "note": forms.Textarea(attrs={"class": "crm-textarea", "rows": 3, "placeholder": "Add detailed activity log, attendees, decision points..."}),
        }


class CSVImportForm(forms.Form):
    TARGET_CHOICES = [
        ("leads", "Leads"),
        ("contacts", "Contacts"),
        ("companies", "Companies"),
    ]
    target = forms.ChoiceField(
        choices=TARGET_CHOICES,
        widget=forms.Select(attrs={"class": "crm-select"})
    )
    file = forms.FileField(
        label="Select CSV File",
        widget=forms.FileInput(attrs={"class": "crm-file-input", "accept": ".csv"})
    )

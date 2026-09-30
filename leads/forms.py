from django import forms
from core.forms import StyledFormMixin, date_widget
from accounts.models import User
from .models import Lead, Activity


class LeadForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Lead
        fields = ["name", "company", "email", "phone", "source", "lead_type", "status", "value", "next_followup", "owner", "notes"]
        labels = {
            "name": "Lead Name",
            "phone": "Phone Number",
            "email": "Email Address",
            "source": "Lead Source",
            "lead_type": "Lead Type",
        }
        widgets = {"next_followup": date_widget(), "notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *a, user=None, **kw):
        super().__init__(*a, **kw)
        if user and user.has_perm("leads.view_all_leads"):
            self.fields["owner"].queryset = User.objects.filter(is_active=True)
        else:
            del self.fields["owner"]  # plain sales users always own what they create


class ActivityForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Activity
        fields = ["kind", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 2, "placeholder": "What happened?"})}

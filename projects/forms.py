from django import forms
from core.forms import StyledFormMixin, date_widget
from accounts.models import User
from .models import Project


class ProjectForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "client", "status", "budget", "start_date", "end_date", "manager", "description"]
        widgets = {"start_date": date_widget(), "end_date": date_widget(), "description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["manager"].queryset = User.objects.filter(is_active=True)

from django import forms

from django.contrib.auth import get_user_model
from leads.models import Lead
from projects.models import Project

def date_widget():
    return forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class StyledFormMixin:
    """Adds CSS classes to every widget so forms match the app theme."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        for f in self.fields.values():
            cls = "check" if isinstance(f.widget, forms.CheckboxInput) else "input"
            f.widget.attrs["class"] = (f.widget.attrs.get("class", "") + " " + cls).strip()


class TaskForm(StyledFormMixin, forms.Form):

    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Task title"
            }
        )
    )

    due_date = forms.DateField(
        required=False,
        widget=date_widget()
    )

    assigned_to = forms.ModelChoiceField(
        queryset=get_user_model().objects.filter(
            is_active=True
        ),
        empty_label="Assign to..."
    )

    lead = forms.ModelChoiceField(
        queryset=Lead.objects.all(),
        required=False,
        empty_label="No lead"
    )

    project = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        required=False,
        empty_label="No project"
    )
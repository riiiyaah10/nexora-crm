from django import forms
from django.contrib.auth.models import Group
from core.forms import StyledFormMixin
from .models import User


class EmailForm(StyledFormMixin, forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": "you@company.com",
                "autofocus": True,
            }
        )
    )


class RegisterForm(StyledFormMixin, forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "placeholder": "Your full name",
            "autofocus": True,
        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "placeholder": "you@company.com",
        })
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists. Please sign in."
            )

        return email


class OTPForm(StyledFormMixin, forms.Form):
    otp = forms.RegexField(
        regex=r"^\d{6}$",
        max_length=6,
        label="6-digit OTP",
        error_messages={
            "invalid": "Enter the 6-digit code."
        },
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "autofocus": True,
            }
        )
    )


class UserForm(StyledFormMixin, forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    role = forms.ModelChoiceField(
        Group.objects.all(),
        empty_label=None
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        label="Active (can sign in)"
    )

    def __init__(self, *a, instance=None, **kw):
        super().__init__(*a, **kw)
        self.instance = instance

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        qs = User.objects.filter(email__iexact=email)

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                "A user with this email already exists."
            )

        return email
import hashlib, hmac, secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.models import Group
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.core.mail import send_mail

from core.audit import log
from core.models import AuditLog
from core.permissions import perm_required
from .forms import EmailForm, OTPForm, UserForm, RegisterForm
from .models import User, OTP
from .permissions import grid, perm_objects, codes_of, ALL_CODES


def _hash(email, code):
    return hmac.new(settings.SECRET_KEY.encode(), f"{email}:{code}".encode(), hashlib.sha256).hexdigest()


# ------------------------------------------------------------------ OTP login
def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    nxt = request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        request.session["login_next"] = nxt
    form = EmailForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        recent = OTP.objects.filter(email=email).order_by("-id").first()
        if recent and (timezone.now() - recent.created_at).total_seconds() < settings.OTP_RESEND_SECONDS:
            messages.error(request, f"Please wait {settings.OTP_RESEND_SECONDS} seconds before requesting another OTP.")
            return render(request, "accounts/login.html", {"form": form})
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:  # same response either way, so emails can't be guessed
            code = f"{secrets.randbelow(10**6):06d}"
            OTP.objects.create(email=email, code_hash=_hash(email, code),
                               expires_at=timezone.now() + timedelta(minutes=settings.OTP_TTL_MIN))
            try:
                send_mail("Your login OTP", f"Your one-time password is {code}. It is valid for "
                          f"{settings.OTP_TTL_MIN} minutes. Do not share it.", settings.DEFAULT_FROM_EMAIL, [email])
            except Exception:
                messages.error(request, "Could not send the email. Check the SMTP settings.")
                return render(request, "accounts/login.html", {"form": form})
        request.session["otp_email"] = email
        messages.info(request, "If this email is registered, an OTP has been sent.")
        return redirect("accounts:verify")
    return render(request, "accounts/login.html", {"form": form})

def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = RegisterForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        name = form.cleaned_data["name"].strip()
        email = form.cleaned_data["email"].strip().lower()

        # Prevent duplicate accounts
        if User.objects.filter(email__iexact=email).exists():
            messages.error(
                request,
                "An account with this email already exists. Please sign in."
            )
            return redirect("accounts:login")

        # Check resend cooldown
        recent = OTP.objects.filter(
            email=email
        ).order_by("-id").first()

        if recent and (
            timezone.now() - recent.created_at
        ).total_seconds() < settings.OTP_RESEND_SECONDS:

            messages.error(
                request,
                f"Please wait {settings.OTP_RESEND_SECONDS} "
                "seconds before requesting another OTP."
            )

            return render(
                request,
                "accounts/register.html",
                {"form": form}
            )

        # Generate OTP
        code = f"{secrets.randbelow(10**6):06d}"

        OTP.objects.create(
            email=email,
            code_hash=_hash(email, code),
            expires_at=timezone.now()
            + timedelta(minutes=settings.OTP_TTL_MIN)
        )

        # Store registration information temporarily
        request.session["registration_email"] = email
        request.session["registration_name"] = name
        request.session["otp_purpose"] = "registration"

        try:
            send_mail(
                "Your CRM verification OTP",
                f"Your verification code is {code}. "
                f"It is valid for {settings.OTP_TTL_MIN} minutes. "
                "Do not share this code with anyone.",
                settings.DEFAULT_FROM_EMAIL,
                [email],
            )

        except Exception:
            messages.error(
                request,
                "Could not send the verification email. "
                "Please try again later."
            )

            return render(
                request,
                "accounts/register.html",
                {"form": form}
            )

        messages.success(
            request,
            "Verification code sent to your email."
        )

        return redirect("accounts:register_verify")

    return render(
        request,
        "accounts/register.html",
        {"form": form}
    )


def verify_view(request):
    email = request.session.get("otp_email")
    if not email:
        return redirect("accounts:login")
    form = OTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        rec = OTP.objects.filter(email=email, used=False).order_by("-id").first()
        if not rec or rec.expires_at < timezone.now() or rec.attempts >= settings.OTP_MAX_ATTEMPTS:
            messages.error(request, "OTP expired or too many attempts. Request a new one.")
            return redirect("accounts:login")
        rec.attempts += 1
        if hmac.compare_digest(rec.code_hash, _hash(email, form.cleaned_data["otp"])):
            rec.used = True
            rec.save()
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            nxt = request.session.get("login_next")
            request.session.flush()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            log(user, "login")
            return redirect(nxt or "home")
        rec.save()
        messages.error(request, "Invalid OTP.")
    return render(request, "accounts/verify.html", {"form": form, "email": email})

def register_verify_view(request):
    email = request.session.get("registration_email")
    name = request.session.get("registration_name")

    if not email or not name:
        return redirect("accounts:register")

    form = OTPForm(request.POST or None)

    if request.method == "POST" and form.is_valid():

        rec = OTP.objects.filter(
            email=email,
            used=False
        ).order_by("-id").first()

        if (
            not rec
            or rec.expires_at < timezone.now()
            or rec.attempts >= settings.OTP_MAX_ATTEMPTS
        ):
            messages.error(
                request,
                "OTP expired or too many attempts. Please register again."
            )
            return redirect("accounts:register")

        rec.attempts += 1

        if hmac.compare_digest(
            rec.code_hash,
            _hash(email, form.cleaned_data["otp"])
        ):
            rec.used = True
            rec.save()

            # Check again in case account was created
            # while the OTP was pending.
            user = User.objects.filter(
                email__iexact=email
            ).first()

            if user:
                messages.error(
                    request,
                    "An account with this email already exists. "
                    "Please sign in."
                )

                request.session.flush()

                return redirect("accounts:login")

            # Create the new account
            user = User.objects.create_user(
                email=email,
                name=name
            )

            # Clear temporary registration data
            request.session.flush()

            # Log the user in
            login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend"
            )

            log(user, "register")

            messages.success(
                request,
                "Your account has been created successfully."
            )

            return redirect("home")

        rec.save()

        messages.error(
            request,
            "Invalid OTP."
        )

    return render(
        request,
        "accounts/register_verify.html",
        {
            "form": form,
            "email": email,
            "name": name,
        }
    )

def demo_login_view(request):
    """
    Public entry point for recruiters and portfolio evaluators.
    Creates or retrieves the dedicated Demo Viewer account, establishes session,
    and redirects directly to the operational dashboard without requiring email or OTP.
    """
    from accounts.services import get_or_create_demo_viewer
    demo_user = get_or_create_demo_viewer()
    login(request, demo_user, backend="django.contrib.auth.backends.ModelBackend")
    request.session["is_demo_mode"] = True
    messages.info(request, "Welcome to NEXORA! You are browsing in read-only Demo Mode.")
    return redirect("home")


def demo_exit_view(request):
    """Exit Demo Mode and return to the primary login screen."""
    logout(request)
    messages.info(request, "You have exited Demo Mode.")
    return redirect("accounts:login")


@require_POST
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


# ------------------------------------------------------------------ users / roles / audit
@perm_required("accounts.manage_users")
def user_list(request):
    users = User.objects.prefetch_related("groups", "user_permissions")
    return render(request, "accounts/users.html", {"users": users})


@perm_required("accounts.manage_users")
def user_edit(request, pk=None):
    user = get_object_or_404(User, pk=pk) if pk else None
    if user and user.pk == request.user.pk:
        messages.error(request, "You cannot change your own access.")
        return redirect("accounts:users")
    if request.method == "POST":
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            d = form.cleaned_data
            if user is None:
                user = User.objects.create_user(d["email"], name=d["name"])
            user.name, user.email, user.is_active = d["name"], d["email"], d["is_active"]
            user.save()
            user.groups.set([d["role"]])
            user.user_permissions.set(perm_objects(request.POST.getlist("perm")))
            log(request.user, "update" if pk else "create", user, f"{user.email} role={d['role']}")
            messages.success(request, f"Saved {user.name}.")
            return redirect("accounts:users")
        checked = set(request.POST.getlist("perm"))
    else:
        form = UserForm(instance=user, initial={
            "name": user.name, "email": user.email, "is_active": user.is_active,
            "role": user.groups.first()} if user else None)
        checked = codes_of(user.user_permissions.all()) if user else set()
    return render(request, "accounts/user_form.html", {"form": form, "target": user, "grid": grid(checked)})


@perm_required("accounts.manage_users")
def roles(request):
    if request.method == "POST":
        if request.POST.get("action") == "create":
            name = request.POST.get("name", "").strip()
            if name and not Group.objects.filter(name__iexact=name).exists():
                Group.objects.create(name=name)
                log(request.user, "create", None, f"role {name}")
                messages.success(request, f"Role '{name}' created. Tick its permissions below.")
            else:
                messages.error(request, "Enter a unique role name.")
        else:
            group = get_object_or_404(Group, pk=request.POST.get("group_id"))
            codes = ALL_CODES if group.name == "Admin" else request.POST.getlist("perm")
            group.permissions.set(perm_objects(codes))
            log(request.user, "update", group, f"role {group.name} permissions")
            messages.success(request, f"Permissions updated for {group.name}.")
        return redirect("accounts:roles")
    data = [(g, grid(codes_of(g.permissions.all()))) for g in Group.objects.order_by("name")]
    return render(request, "accounts/roles.html", {"roles": data})


@perm_required("accounts.manage_users")
def audit_log(request):
    page = Paginator(AuditLog.objects.select_related("user"), 30).get_page(request.GET.get("page"))
    return render(request, "accounts/audit.html", {"page": page})

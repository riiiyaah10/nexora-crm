"""Middleware for NEXORA CRM."""

from django.core.exceptions import PermissionDenied
from django.urls import resolve


class DemoModeReadOnlyMiddleware:
    """
    Enforces server-side read-only security for Demo Mode sessions.
    Users authenticated under the 'Demo Viewer' role or session cannot execute
    state-changing HTTP operations (POST, PUT, PATCH, DELETE), except for
    exiting demo mode or signing out.
    """

    ALLOWED_ACTION_URLS = {
        "accounts:demo_exit",
        "accounts:logout",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_demo = False

        if request.user.is_authenticated:
            is_demo = (
                getattr(request.user, "role", "") == "Demo Viewer"
                or request.user.groups.filter(name="Demo Viewer").exists()
                or bool(request.session.get("is_demo_mode", False))
            )

        request.is_demo_mode = is_demo

        if is_demo and request.method in ("POST", "PUT", "PATCH", "DELETE"):
            try:
                resolved = resolve(request.path_info)
                url_name = f"{resolved.namespace}:{resolved.url_name}" if resolved.namespace else resolved.url_name
            except Exception:
                url_name = None

            if url_name not in self.ALLOWED_ACTION_URLS:
                raise PermissionDenied(
                    "NEXORA is operating in read-only Demo Mode. Changes cannot be saved."
                )

        return self.get_response(request)

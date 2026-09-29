from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def _check(request, perms):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    if not all(request.user.has_perm(p) for p in perms):
        raise PermissionDenied  # renders templates/403.html  ->  "Access Denied"
    return None


def perm_required(*perms):
    """Function-view decorator: login + all permissions, otherwise Access Denied (403)."""
    def deco(view):
        @wraps(view)
        def wrapper(request, *a, **kw):
            denied = _check(request, perms)
            return denied if denied else view(request, *a, **kw)
        return wrapper
    return deco


class PermMixin:
    """Class-based-view mixin. Set required_perms = ("app.codename", ...)."""
    required_perms = ()

    def dispatch(self, request, *a, **kw):
        denied = _check(request, self.required_perms)
        return denied if denied else super().dispatch(request, *a, **kw)

def crm_context(request):
    unread_count = 0
    is_demo_mode = False

    if request.user.is_authenticated:
        from .models import Notification
        unread_count = Notification.objects.filter(user=request.user, read=False).count()
        is_demo_mode = (
            getattr(request.user, "role", "") == "Demo Viewer"
            or request.user.groups.filter(name="Demo Viewer").exists()
            or bool(request.session.get("is_demo_mode", False))
        )

    return {
        "unread_notif_count": unread_count,
        "is_demo_mode": is_demo_mode,
    }

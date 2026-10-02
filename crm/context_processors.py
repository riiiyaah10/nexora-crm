from django.core.cache import cache


def crm_context(request):
    unread_count = 0
    is_demo_mode = False

    if request.user.is_authenticated:
        cache_key = f"notif_unread_{request.user.pk}"
        unread_count = cache.get(cache_key)
        if unread_count is None:
            from .models import Notification
            unread_count = Notification.objects.filter(user=request.user, read=False).count()
            cache.set(cache_key, unread_count, 30)

        is_demo_mode = getattr(
            request,
            "is_demo_mode",
            bool(request.session.get("is_demo_mode", False))
        )

    return {
        "unread_notif_count": unread_count,
        "is_demo_mode": is_demo_mode,
    }

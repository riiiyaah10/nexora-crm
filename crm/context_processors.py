def crm_context(request):
    if request.user.is_authenticated:
        from .models import Notification
        unread_count = Notification.objects.filter(user=request.user, read=False).count()
        return {
            "unread_notif_count": unread_count,
        }
    return {"unread_notif_count": 0}

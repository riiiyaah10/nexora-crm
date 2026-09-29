from .models import AuditLog


def log(user, action, obj=None, detail=""):
    AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        entity=obj.__class__.__name__ if obj is not None else "",
        entity_id=getattr(obj, "pk", None),
        detail=(detail or (str(obj) if obj is not None else ""))[:255],
    )

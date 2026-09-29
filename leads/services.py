from .models import Lead


def visible_leads(user):
    """Users without 'view all leads' only ever see the leads they own."""
    qs = Lead.objects.select_related("owner")
    return qs if user.has_perm("leads.view_all_leads") else qs.filter(owner=user)

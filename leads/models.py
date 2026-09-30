from django.conf import settings
from django.db import models

STATUSES = ["New", "Contacted", "Qualified", "Proposal", "Won", "Lost"]
KINDS = ["Note", "Call", "Email", "Meeting", "WhatsApp"]
SOURCES = ["Instagram", "Facebook", "Google", "Website", "Organic"]
LEAD_TYPES = ["Organic", "Junk"]


class Lead(models.Model):
    name = models.CharField(max_length=100)
    company = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    source = models.CharField(max_length=50, choices=[(s, s) for s in SOURCES], default="Website", blank=True, db_index=True, help_text="Channel where lead originated")
    lead_type = models.CharField(max_length=20, choices=[(t, t) for t in LEAD_TYPES], default="Organic", db_index=True, help_text="Classification: Organic or Junk")
    status = models.CharField(max_length=20, choices=[(s, s) for s in STATUSES], default="New", db_index=True)
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Expected deal value (₹)")
    next_followup = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="leads")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]
        permissions = [("view_all_leads", "Can view all leads (not just own)")]

    def __str__(self):
        return f"{self.name} ({self.company})" if self.company else self.name


class Activity(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="activities")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    kind = models.CharField(max_length=20, choices=[(k, k) for k in KINDS], default="Note")
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

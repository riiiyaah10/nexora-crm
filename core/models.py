from datetime import date
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=30)
    entity = models.CharField(max_length=40, blank=True)
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    detail = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.action} {self.entity} {self.detail}"


class Task(models.Model):
    title = models.CharField(max_length=200)
    due_date = models.DateField(null=True, blank=True)
    done = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                                    related_name="tasks")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                                   related_name="+")
    lead = models.ForeignKey("leads.Lead", null=True, blank=True, on_delete=models.CASCADE, related_name="tasks")
    project = models.ForeignKey("projects.Project", null=True, blank=True, on_delete=models.CASCADE,
                                related_name="tasks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["done", "due_date", "id"]
        permissions = [("view_dashboard", "Can view dashboard")]

    @property
    def overdue(self):
        return bool(self.due_date and not self.done and self.due_date < date.today())

    def __str__(self):
        return self.title

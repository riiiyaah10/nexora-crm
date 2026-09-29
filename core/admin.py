from django.contrib import admin
from .models import Task, AuditLog

admin.site.register(Task)
admin.site.register(AuditLog)

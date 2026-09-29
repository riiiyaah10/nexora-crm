from django.conf import settings
from django.db import models


INDUSTRIES = [
    ("Technology", "Technology / Software"),
    ("Finance", "Finance / Banking / Insurance"),
    ("Healthcare", "Healthcare / Pharmaceuticals"),
    ("Manufacturing", "Manufacturing & Industrial"),
    ("Retail", "Retail / E-Commerce"),
    ("Consulting", "Consulting & Professional Services"),
    ("RealEstate", "Real Estate & Construction"),
    ("Education", "Education & Training"),
    ("Logistics", "Logistics & Supply Chain"),
    ("Other", "Other Industry"),
]


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=20, default="#8b5cf6")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Company(models.Model):
    name = models.CharField(max_length=150, unique=True, db_index=True)
    domain = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=80, blank=True, choices=INDUSTRIES)
    website = models.URLField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    annual_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0, help_text="Annual revenue / contract base (₹)")
    employee_count = models.PositiveIntegerField(null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="companies")
    tags = models.ManyToManyField(Tag, blank=True, related_name="companies")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Companies"
        permissions = [
            ("view_reports", "Can view CRM analytics & reports"),
            ("import_data", "Can import CRM data"),
            ("export_data", "Can export CRM data"),
        ]

    def __str__(self):
        return self.name


class Contact(models.Model):
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80, blank=True)
    email = models.EmailField(blank=True, db_index=True)
    phone = models.CharField(max_length=40, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL, related_name="contacts")
    lead = models.ForeignKey("leads.Lead", null=True, blank=True, on_delete=models.SET_NULL, related_name="contacts")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="contacts")
    notes = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="contacts")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["first_name", "last_name"]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.full_name or self.email or f"Contact #{self.pk}"


class UnifiedActivity(models.Model):
    KINDS = [
        ("Call", "Phone Call"),
        ("Email", "Email"),
        ("Meeting", "Meeting / Demo"),
        ("Note", "Internal Note"),
        ("StatusChange", "Status Transition"),
        ("Task", "Deliverable Event"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    kind = models.CharField(max_length=20, choices=KINDS, default="Note")
    title = models.CharField(max_length=200)
    note = models.TextField(blank=True)
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE, related_name="activities")
    contact = models.ForeignKey(Contact, null=True, blank=True, on_delete=models.CASCADE, related_name="activities")
    lead = models.ForeignKey("leads.Lead", null=True, blank=True, on_delete=models.CASCADE, related_name="unified_activities")
    project = models.ForeignKey("projects.Project", null=True, blank=True, on_delete=models.CASCADE, related_name="unified_activities")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"[{self.kind}] {self.title}"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=150)
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True)
    level = models.CharField(max_length=20, default="info")  # info, warning, success, alert
    read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.title} for {self.user.email}"


class SavedFilter(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_filters")
    module = models.CharField(max_length=40, db_index=True)  # leads, contacts, companies, projects
    name = models.CharField(max_length=80)
    query_string = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.user.email} - {self.module}: {self.name}"

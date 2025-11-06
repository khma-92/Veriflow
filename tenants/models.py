from django.db import models
from django.utils import timezone


class Plan(models.Model):
    """
    Plan tarifaire/logistique (Free/Pro/Enterprise, etc.)
    - slug: identifiant stable
    - rate limits: per_minute / per_day
    - quotas: JSON (ex: {"liveness_monthly": 5000, "ocr_monthly": 2000, ...})
    - unit_prices: JSON (ex: {"liveness": 0.02, "ocr": 0.08, ...}) pour metering.py
    - sla: texte court (ex: "99.5%")
    - region: indice régional (ex: "eu-west-1", "af-west-1")
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    active = models.BooleanField(default=True)

    per_minute = models.PositiveIntegerField(default=60)
    per_day = models.PositiveIntegerField(default=50000)

    quotas = models.JSONField(default=dict, blank=True)
    unit_prices = models.JSONField(default=dict, blank=True)

    sla = models.CharField(max_length=32, blank=True, default="")
    region = models.CharField(max_length=64, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "plans"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.slug} ({'active' if self.active else 'inactive'})"


class Tenant(models.Model):
    """
    Client (tenant) multi-tenant logique.
    - plan: FK vers Plan
    - country_code: ISO-3166 alpha-2 (ex: "CI", "FR")
    - support_email: contact support du client
    - webhook_url: URL par défaut (peut être surchargée par job)
    - status: ACTIVE|SUSPENDED
    - metadata: JSON libre (tags, groupe, référent, ...)
    """
    STATUS_ACTIVE = "active"
    STATUS_SUSPENDED = "suspended"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_SUSPENDED, "Suspended"),
    ]

    name = models.CharField(max_length=150, unique=True)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="tenants")
    country_code = models.CharField(max_length=2, blank=True, default="")
    support_email = models.EmailField(blank=True, default="")
    webhook_url = models.URLField(blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_usage_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tenants"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} [{self.plan.slug}]"

    @property
    def is_active(self) -> bool:
        return self.status == self.STATUS_ACTIVE

    def touch_usage(self):
        self.last_usage_at = timezone.now()
        self.save(update_fields=["last_usage_at"])

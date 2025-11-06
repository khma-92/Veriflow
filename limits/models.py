from django.db import models

class TenantLimitOverride(models.Model):
    """
    Surcharges facultatives des limites d'un tenant.
    - per_minute / per_day (entiers) si définis > prioritaire au plan
    - quotas_override: JSON (ex: {"liveness_monthly": 20000}) > prioritaire au plan.quotas
    """
    tenant = models.OneToOneField("tenants.Tenant", on_delete=models.CASCADE, related_name="limits_override")
    per_minute = models.PositiveIntegerField(null=True, blank=True)
    per_day = models.PositiveIntegerField(null=True, blank=True)
    quotas_override = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tenant_limit_overrides"

    def __str__(self) -> str:
        return f"LimitsOverride(tenant={self.tenant_id})"

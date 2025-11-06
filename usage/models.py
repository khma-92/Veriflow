from django.db import models

class UsageEvent(models.Model):
    """
    Événement de consommation (pour facturation & quotas).
    - tenant: qui consomme
    - module: 'liveness' | 'ocr' | 'validate' | 'face_match' | 'workflow' ...
    - job_id: identifiant de job async (nullable)
    - request_id: identifiant corrélation (ex: trace_id / req_xxx)
    - billed: True/False (si facturable)
    - unit_price: prix unitaire au moment T (pour export facturation)
    - amount: quantité (par défaut 1 appel)
    """
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="usage_events")
    module = models.CharField(max_length=64, db_index=True)
    job_id = models.CharField(max_length=64, null=True, blank=True)
    request_id = models.CharField(max_length=64, null=True, blank=True)
    billed = models.BooleanField(default=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    amount = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "usage_events"
        indexes = [
            models.Index(fields=["tenant", "module", "created_at"]),
            models.Index(fields=["tenant", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.tenant_id}:{self.module}@{self.created_at:%Y-%m-%d %H:%M:%S}"

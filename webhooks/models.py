from django.db import models
from django.utils import timezone

class WebhookConfig(models.Model):
    """
    Configuration de webhook par tenant.
    - url: endpoint HTTP(s) du client
    - secret: secret HMAC (chiffré si tu as un KMS; sinon plain:... en DEV)
    - events: liste des événements souscrits (ex: ["job.succeeded","job.failed","quota.threshold","quota.exceeded"])
    - active: activation globale
    - timeout_s: timeout requête
    - max_retries: nb max de tentatives
    - backoff_s: base d'exponential backoff (ex: 5s)
    """
    tenant = models.OneToOneField("tenants.Tenant", on_delete=models.CASCADE, related_name="webhook_config")
    url = models.URLField()
    secret = models.CharField(max_length=255)  # ex: "plain:xxxxx" en DEV ou valeur chiffrée
    events = models.JSONField(default=list, blank=True)
    active = models.BooleanField(default=True)
    timeout_s = models.PositiveIntegerField(default=10)
    max_retries = models.PositiveIntegerField(default=5)
    backoff_s = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "webhook_configs"

    def __str__(self) -> str:
        return f"WebhookConfig(t={self.tenant_id}, active={self.active})"


class WebhookDelivery(models.Model):
    """
    Historique des livraisons (journal immuable).
    - event: nom d'événement envoyé
    - payload: corps JSON envoyé
    - attempt: n° tentative (1..N)
    - status_code: code HTTP reçu (null si exception)
    - ok: succès booléen
    - error: texte d’erreur si exception
    - duration_ms: latence
    """
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="webhook_deliveries")
    config = models.ForeignKey(WebhookConfig, on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries")
    event = models.CharField(max_length=64)
    url = models.URLField()
    attempt = models.PositiveIntegerField(default=1)
    headers = models.JSONField(default=dict, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    status_code = models.IntegerField(null=True, blank=True)
    ok = models.BooleanField(default=False)
    error = models.TextField(blank=True, default="")
    duration_ms = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "webhook_deliveries"
        indexes = [
            models.Index(fields=["tenant", "event", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"WebhookDelivery(t={self.tenant_id}, ev={self.event}, ok={self.ok}, attempt={self.attempt})"

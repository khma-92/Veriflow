from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

# FK vers tenants.Tenant
class ApiKey(models.Model):
    """
    Clé API portée par un tenant; on ne stocke jamais le secret en clair.
    - key_id (public) communiqué au client
    - key_secret_hash: hash PBKDF2 du secret (non réaffiché)
    - allowed_ips: liste optionnelle d'IPs autorisées
    - last_used_at: mis à jour à chaque requête authentifiée
    - expires_at: optionnel ; si dépassé => inactif
    """
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="api_keys")
    key_id = models.CharField(max_length=64, unique=True, db_index=True)
    key_secret_hash = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    allowed_ips = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    name = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        db_table = "api_keys"
        indexes = [models.Index(fields=["tenant", "active"])]

    def __str__(self) -> str:
        return f"{self.tenant_id}:{self.key_id}"

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at <= timezone.now())

    def set_secret(self, raw_secret: str) -> None:
        self.key_secret_hash = make_password(raw_secret)

    def check_secret(self, raw_secret: str) -> bool:
        return check_password(raw_secret, self.key_secret_hash)

    def touch_last_used(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at"])

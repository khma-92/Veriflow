from dataclasses import dataclass
from datetime import datetime
from calendar import monthrange
from django.utils.timezone import now
from django.core.cache import cache
from django.db.models import Sum
from tenants.models import Tenant
from usage.models import UsageEvent

# mapping module -> clé quota plan/override
MODULE_TO_QUOTA_KEY = {
    "liveness": "liveness_monthly",
    "ocr": "ocr_monthly",
    "validate": "validate_monthly",
    "face_match": "face_match_monthly",
    "workflow": "workflow_monthly",
}

@dataclass
class QuotaStatus:
    allowed: bool
    used: int
    limit: int | None  # None => illimité
    remaining: int | None

def _month_bounds(dt: datetime):
    y, m = dt.year, dt.month
    start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = dt.replace(day=monthrange(y, m)[1], hour=23, minute=59, second=59, microsecond=999999)
    return start, end

def _cache_key(tenant_id: int, module: str):
    n = now()
    return f"quota:{tenant_id}:{module}:{n.year}{n.month:02d}"

def get_quota_limit(tenant: Tenant, module: str) -> int | None:
    """Retourne la limite mensuelle (None = illimité). Override > plan."""
    key = MODULE_TO_QUOTA_KEY.get(module)
    if not key:
        return None
    limit = None
    if hasattr(tenant, "limits_override") and tenant.limits_override.quotas_override:
        limit = tenant.limits_override.quotas_override.get(key)
    if limit is None:
        limit = tenant.plan.quotas.get(key)
    return limit  # peut être None

def quota_status(tenant: Tenant, module: str) -> QuotaStatus:
    limit = get_quota_limit(tenant, module)
    if limit is None:
        return QuotaStatus(True, 0, None, None)  # illimité

    ckey = _cache_key(tenant.id, module)
    used = cache.get(ckey)
    if used is None:
        # Fallback DB (au premier appel du mois ou si cache perdu)
        start, end = _month_bounds(now())
        used = (UsageEvent.objects
                .filter(tenant=tenant, module=module, created_at__gte=start, created_at__lte=end)
                .aggregate(total=Sum("amount"))["total"] or 0)
        cache.set(ckey, used, timeout=7 * 24 * 3600)  # 7 jours; sera réactualisé via increment

    remaining = max(limit - used, 0)
    return QuotaStatus(allowed=(used < limit), used=used, limit=limit, remaining=remaining)

def check_and_increment_quota(tenant: Tenant, module: str, amount: int = 1) -> QuotaStatus:
    """
    À appeler dans les endpoints avant d'exécuter le module.
    Incrémente le compteur mensuel en cache si autorisé.
    """
    st = quota_status(tenant, module)
    if st.limit is None:
        return st  # illimité, pas d'incrément utile

    if not st.allowed or (st.remaining is not None and st.remaining < amount):
        return QuotaStatus(False, st.used, st.limit, st.remaining)

    ckey = _cache_key(tenant.id, module)
    new_used = (st.used or 0) + amount
    cache.set(ckey, new_used, timeout=7 * 24 * 3600)
    return QuotaStatus(True, new_used, st.limit, (st.limit - new_used))

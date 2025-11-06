from rest_framework.throttling import SimpleRateThrottle
from django.core.cache import cache
from django.utils import timezone

def _tenant_cache_key(prefix: str, tenant_id: int) -> str:
    return f"{prefix}:{tenant_id}"

def _rate_to_tuple(rate: str):
    # "1000/day" -> (1000, 86400)
    num, period = rate.split("/")
    num = int(num)
    seconds = {"s":1,"sec":1,"second":1,"m":60,"min":60,"minute":60,"h":3600,"hour":3600,"day":86400,"d":86400}[period]
    return num, seconds

def _get_effective_rates(request):
    """
    Calcule les débits effectifs pour le tenant (override > plan).
    Retourne (rate_minute, rate_day) au format DRF "N/min" et "N/day".
    """
    tenant = getattr(request, "tenant", None)
    if not tenant:
        # Pas d’auth HMAC -> pas de throttle ici
        return None, None
    pm = tenant.plan.per_minute
    pd = tenant.plan.per_day
    if hasattr(tenant, "limits_override"):
        if tenant.limits_override.per_minute:
            pm = tenant.limits_override.per_minute
        if tenant.limits_override.per_day:
            pd = tenant.limits_override.per_day
    return f"{pm}/min", f"{pd}/day"

class TenantMinuteThrottle(SimpleRateThrottle):
    scope = "tenant_minute"

    def get_cache_key(self, request, view):
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return None
        return _tenant_cache_key(f"throttle:{self.scope}", tenant.id)

    def get_rate(self):
        # DRF appelle get_rate() sans request; on surcharge allow_request pour utiliser la rate dynamique.
        # Ici, on retourne un fallback (non utilisé si allow_request est redéfini).
        return "1000/min"

    def allow_request(self, request, view):
        rate_minute, _ = _get_effective_rates(request)
        if not rate_minute:
            return True
        self.rate = rate_minute
        return super().allow_request(request, view)

class TenantDailyThrottle(SimpleRateThrottle):
    scope = "tenant_day"

    def get_cache_key(self, request, view):
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return None
        return _tenant_cache_key(f"throttle:{self.scope}", tenant.id)

    def get_rate(self):
        return "100000/day"

    def allow_request(self, request, view):
        _, rate_day = _get_effective_rates(request)
        if not rate_day:
            return True
        self.rate = rate_day
        return super().allow_request(request, view)

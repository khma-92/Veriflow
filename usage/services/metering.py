from decimal import Decimal
from typing import Optional
from django.utils.timezone import now
from usage.models import UsageEvent

def record_usage(*, tenant_id: int, module: str, billed: bool = True,
                 unit_price: Optional[Decimal] = None, amount: int = 1,
                 job_id: str | None = None, request_id: str | None = None) -> UsageEvent:
    """
    Enregistre un event de consommation. unit_price peut être dérivé du Plan (si None).
    """
    from tenants.models import Tenant
    tenant = Tenant.objects.select_related("plan").get(id=tenant_id)
    if unit_price is None:
        unit_price = Decimal(tenant.plan.unit_prices.get(module, 0))
    return UsageEvent.objects.create(
        tenant_id=tenant_id, module=module, billed=billed,
        unit_price=unit_price, amount=amount, job_id=job_id, request_id=request_id
    )

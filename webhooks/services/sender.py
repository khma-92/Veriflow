import json, time
from typing import Optional
from decimal import Decimal
import httpx
from django.utils import timezone
from django.conf import settings

from .signer import sign_payload, HDR_SIG, HDR_TS, HDR_EVT
from ..models import WebhookConfig, WebhookDelivery


def _decrypt_or_plain(secret_field: str) -> bytes:
    """
    DEV: secret peut être stocké en "plain:xxxxx".
    PROD: remplacer par un déchiffrement (Fernet/Vault/KMS).
    """
    if secret_field.startswith("plain:"):
        return secret_field.split("plain:", 1)[1].encode("utf-8")
    # Hook de déchiffrement (même logique que pour apikeys si besoin)
    return secret_field.encode("utf-8")

def build_payload(event: str, tenant_id: int, data: dict) -> dict:
    return {
        "id": f"wh_{int(time.time() * 1000)}",
        "event": event,
        "tenant_id": tenant_id,
        "data": data,
        "version": settings.SPECTACULAR_SETTINGS.get("VERSION", "1.0.0"),
        "sent_at": timezone.now().isoformat(),
    }

def send_webhook(config: WebhookConfig, event: str, data: dict, attempt: int = 1) -> WebhookDelivery:
    """
    Envoi synchrone (utilisé par la tâche Celery). Retourne un enregistrement WebhookDelivery.
    """
    payload = build_payload(event, config.tenant_id, data)
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    secret = _decrypt_or_plain(config.secret)

    ts_ms, sig = sign_payload(secret, event, body)

    headers = {
        "Content-Type": "application/json",
        HDR_EVT: event,
        HDR_TS: ts_ms,
        HDR_SIG: sig,
        "User-Agent": "VeriFlow-Webhook/1.0",
    }

    t0 = time.perf_counter()
    status_code = None
    ok = False
    err = ""
    try:
        with httpx.Client(timeout=config.timeout_s, verify=True) as client:
            resp = client.post(config.url, headers=headers, content=body)
            status_code = resp.status_code
            ok = 200 <= resp.status_code < 300
            if not ok:
                err = f"HTTP {resp.status_code}: {resp.text[:500]}"
    except Exception as e:
        err = str(e)
    duration_ms = int((time.perf_counter() - t0) * 1000)

    delivery = WebhookDelivery.objects.create(
        tenant=config.tenant,
        config=config,
        event=event,
        url=config.url,
        attempt=attempt,
        headers=headers,
        payload=payload,
        status_code=status_code,
        ok=ok,
        error=err,
        duration_ms=duration_ms,
    )
    return delivery

import hmac, hashlib, time
from typing import Tuple
from django.conf import settings

# Entêtes sortants normalisés
HDR_SIG = "X-Webhook-Signature"
HDR_TS = "X-Webhook-Timestamp"
HDR_EVT = "X-Webhook-Event"
ALGO = "HMAC-SHA256"

def sign_payload(secret: bytes, event: str, body_bytes: bytes, ts_ms: int | None = None) -> Tuple[str, str]:
    """
    Signature = hex(HMAC_SHA256(secret, f"{ts}\n{event}\n{body_sha256}"))
    Retourne (timestamp_ms_str, hex_signature)
    """
    if ts_ms is None:
        ts_ms = int(time.time() * 1000)
    body_sha = hashlib.sha256(body_bytes).hexdigest()
    to_sign = f"{ts_ms}\n{event}\n{body_sha}".encode("utf-8")
    sig = hmac.new(secret, to_sign, hashlib.sha256).hexdigest()
    return str(ts_ms), sig

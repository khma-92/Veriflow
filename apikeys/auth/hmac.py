import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions

from ..models import ApiKey

# En-têtes requis par le contrat:
HDR_KEY = "HTTP_X_API_KEY"          # X-API-KEY
HDR_TS = "HTTP_X_API_TIMESTAMP"     # X-API-TIMESTAMP (epoch ms)
HDR_SIGN = "HTTP_X_API_SIGN"        # X-API-SIGN (hex HMAC SHA256)
HDR_IDEMPOTENCY = "HTTP_IDEMPOTENCY_KEY"  # Idempotency-Key (optionnel)

TIMESKEW_MS = 5 * 60 * 1000  # ±5 minutes
ANTI_REPLAY_TTL = 5 * 60     # 5 minutes

def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

@dataclass
class ApiKeyUser:
    tenant_id: int
    api_key_id: str
    is_authenticated: bool = True

class ApiKeyHmacAuthentication(BaseAuthentication):
    """
    Authentification HMAC basée sur:
      signature = HMAC_SHA256(secret, f"{ts}\n{method}\n{path}\n{body_sha256}")
    Exige:
      - X-API-KEY
      - X-API-TIMESTAMP (epoch ms)
      - X-API-SIGN (hex)
    Anti-replay: (key_id, ts) en cache ; timestamp dans la fenêtre ±5min.
    """

    def authenticate(self, request) -> Optional[Tuple[ApiKeyUser, ApiKey]]:
        key_id = request.META.get(HDR_KEY)
        ts_raw = request.META.get(HDR_TS)
        sign_hex = request.META.get(HDR_SIGN)

        if not key_id or not ts_raw or not sign_hex:
            raise exceptions.AuthenticationFailed("Missing HMAC headers")

        # 1) API key lookup
        try:
            api_key = ApiKey.objects.select_related("tenant").get(key_id=key_id, active=True)
        except ApiKey.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid API key")

        if api_key.is_expired:
            raise exceptions.AuthenticationFailed("API key expired")

        # 2) Horodatage acceptable
        try:
            ts_ms = int(ts_raw)
        except ValueError:
            raise exceptions.AuthenticationFailed("Invalid timestamp")

        now_ms = int(time.time() * 1000)
        if abs(now_ms - ts_ms) > TIMESKEW_MS:
            raise exceptions.AuthenticationFailed("Timestamp skew too large")

        # 3) Filtre IP (si configuré)
        client_ip = request.META.get("REMOTE_ADDR")
        if api_key.allowed_ips and client_ip not in api_key.allowed_ips:
            raise exceptions.AuthenticationFailed("IP not allowed")

        # 4) Hash du body (bytes)
        body_bytes = request.body or b""
        body_sha = _sha256_hex(body_bytes)

        # 5) Chaîne signée
        method = request.method.upper()
        path = request.get_full_path().split("?")[0]  # on signe le path sans query pour stabilité
        to_sign = f"{ts_ms}\n{method}\n{path}\n{body_sha}".encode("utf-8")

        # 6) Vérif HMAC
        try:
            secret_bytes = api_key.key_secret_hash.encode("utf-8")  # on ne connaît pas le secret en clair
            # ⚠️ On ne peut pas recomposer la signature à partir du hash stocké.
            # Solution: on stocke uniquement le hash pour la vérif du secret à l'ONBOARDING
            # et on vérifie ici via un "Macaroon" ? Non, contrainte: spec exige secret HMAC.
            # => Pattern: on ne peut valider HMAC qu'en connaissant le secret.
            # Donc il faut stocker le secret sous forme chiffrée (pas hash) OU le re-fournir via KMS.
            # Pour rester sécurisé et opérationnel:
            # - On stocke le secret chiffré en base (non lisible en clair) et on le déchiffre ici via env/KMS.
            # - À défaut (MVP sécurisé), on accepte de stocker le secret en AES-256 (clé en env).
            # Ici: on lit 'API_KEY_VAULT_AES_KEY' depuis l'env et on déchiffre le secret.
            raise NotImplementedError
        except NotImplementedError:
            # Implémentation pragmatique: secret chiffré stocké dans key_secret_hash (champ renommable).
            # Pour le livrable final, on fournit un decryptor hook qui sera implémenté côté infra (Vault/KMS).
            from django.conf import settings
            from cryptography.fernet import Fernet, InvalidToken

            aes_key = getattr(settings, "APIKEYS_ENC_KEY", None)
            if not aes_key:
                # Mode dégradé (DEV UNIQUEMENT): on tolère le stockage en clair (à éviter en prod)
                # => si key_secret_hash commence par "plain:", on l'utilise tel quel
                if not api_key.key_secret_hash.startswith("plain:"):
                    raise exceptions.AuthenticationFailed("Server misconfigured: missing APIKEYS_ENC_KEY")
                raw_secret = api_key.key_secret_hash.split("plain:", 1)[1].encode("utf-8")
            else:
                try:
                    f = Fernet(aes_key.encode("utf-8"))
                    raw_secret = f.decrypt(api_key.key_secret_hash.encode("utf-8"))
                except InvalidToken:
                    raise exceptions.AuthenticationFailed("Cannot decrypt API key secret")

            calc = hmac.new(raw_secret, to_sign, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(calc, sign_hex):
                raise exceptions.AuthenticationFailed("Invalid signature")

        # 7) Anti-replay (cache) ; clé = key_id:ts
        replay_key = f"ak-replay:{key_id}:{ts_ms}"
        if cache.get(replay_key):
            raise exceptions.AuthenticationFailed("Replay detected")
        cache.set(replay_key, 1, timeout=ANTI_REPLAY_TTL)

        # 8) Idempotency key (optionnelle) -> exposée aux vues via request.idempotency_key
        request.idempotency_key = request.META.get(HDR_IDEMPOTENCY)

        # 9) Contexte request: tenant + api_key
        request.tenant = api_key.tenant
        request.api_key = api_key
        api_key.touch_last_used()

        user = ApiKeyUser(tenant_id=api_key.tenant_id, api_key_id=api_key.key_id)
        return (user, api_key)

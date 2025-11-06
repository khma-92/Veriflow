from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse

from limits.services.quota import check_and_increment_quota
from usage.services.metering import record_usage
from webhooks.models import WebhookConfig
from webhooks.tasks import deliver_webhook_task

from ..serializers.input import LivenessInputSerializer
from ..serializers.output import LivenessOutputSerializer
from ..services.liveness_service import LivenessService

def maybe_emit_quota_webhooks(tenant, module: str, used: int, limit: int | None, remaining: int | None):
    """
    Envoie un webhook 'quota.threshold' si on vient de passer sous 20% restants,
    et 'quota.exceeded' si remaining == 0. (idempotence best-effort via le client)
    """
    if limit is None:
        return

    if remaining == 0:
        for cfg in WebhookConfig.objects.filter(tenant=tenant, active=True, events__contains=["quota.exceeded"]):
            deliver_webhook_task.delay(cfg.id, "quota.exceeded", {
                "module": module,
                "used": used,
                "limit": limit,
                "remaining": remaining
            }, attempt=1)
        return

    # seuil 80% atteint (20% restants)
    if limit > 0 and remaining is not None:
        ratio_used = used / limit
        if ratio_used >= 0.80:
            for cfg in WebhookConfig.objects.filter(tenant=tenant, active=True, events__contains=["quota.threshold"]):
                deliver_webhook_task.delay(cfg.id, "quota.threshold", {
                    "module": module,
                    "used": used,
                    "limit": limit,
                    "remaining": remaining
                }, attempt=1)

@extend_schema(
    tags=["Liveness"],
    request=LivenessInputSerializer,
    responses={
        200: OpenApiResponse(response=LivenessOutputSerializer,
             description="Résultat liveness/anti-spoof"),
        400: OpenApiResponse(description="INVALID_IMAGE_*"),
        429: OpenApiResponse(description="QUOTA_EXCEEDED"),
    },
    examples=[
        OpenApiExample(
            "Exemple requête",
            value={
                "image_live_base64": "<...>",
                "hints": {"pose": True, "blink": True}
            },
            request_only=True,
        ),
        OpenApiExample(
            "Exemple réponse",
            value={
                "is_live": True,
                "spoof_type": "none",
                "confidence": 0.93,
                "processing_ms": 428,
                "usage": {"module": "liveness", "billed": True}
            },
            response_only=True,
        ),
    ],
)
class LivenessAnalyzeView(APIView):
    """
    POST /liveness/analyze
    Auth: HMAC (clé tenant)
    Quotas: module 'liveness'
    Facturation: 1 unité / appel
    """
    serializer_class = LivenessInputSerializer

    def post(self, request):
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return Response({"error":{"code":"UNAUTHORIZED","message":"Tenant auth required"}}, status=401)

        # 1) Quota
        qs = check_and_increment_quota(tenant, module="liveness", amount=1)
        if not qs.allowed:
            return Response(
                {"error":{"code":"QUOTA_EXCEEDED","message":"Monthly liveness quota exceeded",
                          "details":{"used":qs.used,"limit":qs.limit,"remaining":qs.remaining}}},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # 2) Validate input
        ser = self.serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        image_live_base64 = ser.validated_data["image_live_base64"]
        hints = ser.validated_data.get("hints", {})

        # 3) Service
        svc = LivenessService()
        try:
            res = svc.run(image_live_base64=image_live_base64, hints=hints)
        except ValueError as e:
            return Response(
                {"error":{"code":"INVALID_IMAGE","message":str(e)}},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4) Metering
        record_usage(
            tenant_id=tenant.id,
            module="liveness",
            billed=True,
            job_id=None,
            request_id=getattr(request, "idempotency_key", None)
        )

        # (Optionnel) 5) Webhooks seuils
        maybe_emit_quota_webhooks(tenant, "liveness", used=qs.used, limit=qs.limit, remaining=qs.remaining)

        return Response({
            "is_live": res.is_live,
            "spoof_type": res.spoof_type,
            "confidence": res.confidence,
            "processing_ms": res.processing_ms,
            "usage": {"module": "liveness", "billed": True}
        }, status=200)

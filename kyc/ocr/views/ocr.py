from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse

from limits.services.quota import check_and_increment_quota
from usage.services.metering import record_usage
from webhooks.models import WebhookConfig
from webhooks.tasks import deliver_webhook_task

from ..serializers.input import OcrInputSerializer
from ..serializers.output import OcrOutputSerializer
from ..services.ocr_service import OcrService

def maybe_emit_quota_webhooks(tenant, module: str, used: int, limit: int | None, remaining: int | None):
    if limit is None:
        return
    if remaining == 0:
        for cfg in WebhookConfig.objects.filter(tenant=tenant, active=True, events__contains=["quota.exceeded"]):
            deliver_webhook_task.delay(cfg.id, "quota.exceeded", {
                "module": module, "used": used, "limit": limit, "remaining": remaining
            }, attempt=1)
        return
    if limit > 0 and remaining is not None and used/limit >= 0.80:
        for cfg in WebhookConfig.objects.filter(tenant=tenant, active=True, events__contains=["quota.threshold"]):
            deliver_webhook_task.delay(cfg.id, "quota.threshold", {
                "module": module, "used": used, "limit": limit, "remaining": remaining
            }, attempt=1)

@extend_schema(
    tags=["Document OCR"],
    request=OcrInputSerializer,
    responses={
        200: OpenApiResponse(response=OcrOutputSerializer, description="OCR + détection type/pays"),
        400: OpenApiResponse(description="INVALID_*"),
        429: OpenApiResponse(description="QUOTA_EXCEEDED"),
    },
    examples=[
        OpenApiExample(
            "Requête",
            value={
                "image_front_base64": "<...>",
                "image_back_base64": "<optional>",
                "document_hint": "auto",
                "country_hint": "auto"
            },
            request_only=True,
        ),
        OpenApiExample(
            "Réponse",
            value={
                "detected": {"type": "passport", "country": "CIV", "confidence": 0.88},
                "fields": {
                    "surname": "KOFFI",
                    "given_names": "JEAN MARIE",
                    "dob": "1999-08-16",
                    "document_number": "ABC123456",
                    "sex": "M",
                    "nationality": "CIV",
                    "expiry_date": "2029-08-15",
                    "mrz": "P<CIVKOFFI<<JEAN<MARIE<<<<<<<<<<<<<<<<<..."
                },
                "images": {"face_crop_base64": "<...>"},
                "quality": {"sharpness": 0.81, "glare": 0.07},
                "usage": {"module": "ocr", "billed": True}
            },
            response_only=True,
        ),
    ],
)
class DocumentOcrView(APIView):
    """
    POST /document/ocr
    Auth: HMAC (clé tenant)
    Module quota: "ocr"
    Facturation: 1 par appel
    """
    serializer_class = OcrInputSerializer

    def post(self, request):
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return Response({"error":{"code":"UNAUTHORIZED","message":"Tenant auth required"}}, status=401)

        # Quota
        qs = check_and_increment_quota(tenant, module="ocr", amount=1)
        if not qs.allowed:
            return Response(
                {"error":{"code":"QUOTA_EXCEEDED","message":"Monthly OCR quota exceeded",
                          "details":{"used":qs.used,"limit":qs.limit,"remaining":qs.remaining}}},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # Validate
        ser = self.serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        svc = OcrService()
        try:
            res = svc.run(
                image_front_base64=data["image_front_base64"],
                image_back_base64=data.get("image_back_base64"),
                document_hint=data.get("document_hint", "auto"),
                country_hint=data.get("country_hint", "auto"),
            )
        except ValueError as e:
            return Response({"error":{"code":"INVALID_IMAGE","message":str(e)}}, status=400)

        # Metering
        record_usage(
            tenant_id=tenant.id,
            module="ocr",
            billed=True,
            job_id=None,
            request_id=getattr(request, "idempotency_key", None),
        )

        # Webhooks seuils
        maybe_emit_quota_webhooks(tenant, "ocr", used=qs.used, limit=qs.limit, remaining=qs.remaining)

        return Response({
            "detected": {"type": res.detected.type, "country": res.detected.country, "confidence": res.detected.confidence},
            "fields": res.fields,
            "images": {"face_crop_base64": res.face_crop_base64},
            "quality": res.quality,
            "usage": {"module": "ocr", "billed": True},
        }, status=200)

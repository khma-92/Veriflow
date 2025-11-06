from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse

from limits.services.quota import check_and_increment_quota
from usage.services.metering import record_usage
from webhooks.models import WebhookConfig
from webhooks.tasks import deliver_webhook_task

from ..serializers.input import ValidateInputSerializer
from ..serializers.output import ValidateOutputSerializer
from ..services.validator import validate_document

def maybe_emit_quota_webhooks(tenant, module: str, used, limit, remaining):
    if limit is None: return
    if remaining == 0:
        for cfg in WebhookConfig.objects.filter(tenant=tenant, active=True, events__contains=["quota.exceeded"]):
            deliver_webhook_task.delay(cfg.id, "quota.exceeded", {"module":module,"used":used,"limit":limit,"remaining":remaining}, 1)
    elif used/limit >= 0.80:
        for cfg in WebhookConfig.objects.filter(tenant=tenant, active=True, events__contains=["quota.threshold"]):
            deliver_webhook_task.delay(cfg.id, "quota.threshold", {"module":module,"used":used,"limit":limit,"remaining":remaining}, 1)

@extend_schema(
    tags=["Document Validation"],
    request=ValidateInputSerializer,
    responses={200: OpenApiResponse(ValidateOutputSerializer), 429: OpenApiResponse(description="QUOTA_EXCEEDED")},
    examples=[OpenApiExample("Requête", value={"detected":{"type":"passport","country":"CIV"},"fields":{"mrz":"P<CIV...","dob":"1999-08-16","expiry_date":"2029-08-15"}}, request_only=True)]
)
class DocumentValidateView(APIView):
    def post(self, request):
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return Response({"error":{"code":"UNAUTHORIZED"}}, status=401)

        qs = check_and_increment_quota(tenant, module="validate", amount=1)
        if not qs.allowed:
            return Response({"error":{"code":"QUOTA_EXCEEDED","details":{"used":qs.used,"limit":qs.limit}}}, status=429)

        ser = ValidateInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        res = validate_document(detected=ser.validated_data["detected"], fields=ser.validated_data["fields"])

        record_usage(tenant_id=tenant.id, module="validate", billed=True, job_id=None, request_id=getattr(request,"idempotency_key",None))
        maybe_emit_quota_webhooks(tenant, "validate", qs.used, qs.limit, qs.remaining)

        return Response({"document_valid": res.document_valid, "checks": res.checks, "confidence": res.confidence, "usage":{"module":"validate","billed":True}}, status=200)

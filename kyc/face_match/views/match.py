from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse

from limits.services.quota import check_and_increment_quota
from usage.services.metering import record_usage
from webhooks.models import WebhookConfig
from webhooks.tasks import deliver_webhook_task

from ..serializers.input import FaceMatchInputSerializer
from ..serializers.output import FaceMatchOutputSerializer
from ..services.matcher import face_match

def maybe_emit_quota_webhooks(tenant, module, used, limit, remaining):
    if limit is None: return
    if remaining == 0:
        for cfg in WebhookConfig.objects.filter(tenant=tenant, active=True, events__contains=["quota.exceeded"]):
            deliver_webhook_task.delay(cfg.id, "quota.exceeded", {"module":module,"used":used,"limit":limit,"remaining":remaining}, 1)
    elif used/limit >= 0.80:
        for cfg in WebhookConfig.objects.filter(tenant=tenant, active=True, events__contains=["quota.threshold"]):
            deliver_webhook_task.delay(cfg.id, "quota.threshold", {"module":module,"used":used,"limit":limit,"remaining":remaining}, 1)

@extend_schema(
    tags=["Face Match"],
    request=FaceMatchInputSerializer,
    responses={200: OpenApiResponse(FaceMatchOutputSerializer), 400: OpenApiResponse(description="INVALID_*"), 429: OpenApiResponse(description="QUOTA_EXCEEDED")},
    examples=[OpenApiExample("Réponse", value={"match": True, "similarity": 0.84, "threshold": 0.75}, response_only=True)]
)
class FaceMatchView(APIView):
    def post(self, request):
        tenant = getattr(request, "tenant", None)
        if not tenant: return Response({"error":{"code":"UNAUTHORIZED"}}, status=401)

        qs = check_and_increment_quota(tenant, module="face_match", amount=1)
        if not qs.allowed:
            return Response({"error":{"code":"QUOTA_EXCEEDED"}}, status=429)

        ser = FaceMatchInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            res = face_match(
                image_live_base64=ser.validated_data["image_live_base64"],
                image_ref_base64=ser.validated_data["image_ref_base64"],
                threshold=ser.validated_data.get("threshold", 0.75),
            )
        except ValueError as e:
            return Response({"error":{"code":"INVALID_IMAGE","message":str(e)}}, status=400)

        record_usage(tenant_id=tenant.id, module="face_match", billed=True, job_id=None, request_id=getattr(request,"idempotency_key",None))
        maybe_emit_quota_webhooks(tenant, "face_match", qs.used, qs.limit, qs.remaining)

        return Response({"match": res.match, "similarity": res.similarity, "threshold": ser.validated_data.get("threshold",0.75), "usage":{"module":"face_match","billed":True}}, status=200)

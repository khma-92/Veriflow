from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from jobs.models import Job
from ..serializers.input import WorkflowInputSerializer
from ..serializers.output import WorkflowOutputSerializer
from kyc.workflow.tasks import run_kyc_workflow

@extend_schema(
    tags=["KYC Workflow"],
    request=WorkflowInputSerializer,
    responses={202: OpenApiResponse(WorkflowOutputSerializer)},
    examples=[OpenApiExample("Requête", value={
        "steps": ["liveness","ocr","validate","face_match","score"],
        "inputs": {
          "image_live_base64": "<...>",
          "image_doc_front_base64": "<...>",
          "image_doc_back_base64": "<optional>",
          "face_threshold": 0.75
        },
        "rules": {"min_score_accept": 80, "min_similarity": 0.75, "require_back_image": False},
        "webhook_url": "https://client.example.com/hooks/kyc"
    }, request_only=True)]
)
class KycWorkflowView(APIView):
    """
    POST /kyc/verify → 202 + job_id
    GET /jobs/{id}  → statut et résultat
    """
    def post(self, request):
        tenant = getattr(request, "tenant", None)
        if not tenant: return Response({"error":{"code":"UNAUTHORIZED"}}, status=401)

        ser = WorkflowInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        job = Job.objects.create(
            tenant=tenant,
            steps=ser.validated_data["steps"],
            inputs={**ser.validated_data["inputs"], "rules": ser.validated_data.get("rules", {})},
            status=Job.STATUS_Q,
        )
        run_kyc_workflow.delay(job.id)
        return Response({"job_id": str(job.id), "status": "queued"}, status=202)

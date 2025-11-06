from celery import shared_task
from django.utils import timezone
from jobs.models import Job
from kyc.face_match.services.matcher import face_match
from kyc.validation.services.validator import validate_document
from usage.services.metering import record_usage
from limits.services.quota import check_and_increment_quota
from webhooks.models import WebhookConfig
from webhooks.tasks import deliver_webhook_task

# Réutilise nos services existants
from kyc.liveness.services.liveness_service import LivenessService
from kyc.ocr.services.ocr_service import OcrService

def _emit(tenant, event: str, payload: dict):
    for cfg in WebhookConfig.objects.filter(tenant=tenant, active=True, events__contains=[event]):
        deliver_webhook_task.delay(cfg.id, event, payload, attempt=1)

@shared_task(bind=True, max_retries=0)
def run_kyc_workflow(self, job_id: int):
    job = Job.objects.select_related("tenant").get(id=job_id)
    tenant = job.tenant
    job.status = Job.STATUS_R
    job.started_at = timezone.now()
    job.save(update_fields=["status","started_at"])

    res = {}
    inp = job.inputs or {}
    rules = (inp.get("rules") or {})  # passé via inputs.rules depuis l'API
    min_score_accept = float(rules.get("min_score_accept", 80.0))
    min_similarity = float(rules.get("min_similarity", 0.75))

    try:
        for step in job.steps:
            if step == "liveness":
                qs = check_and_increment_quota(tenant, "liveness", 1)
                if not qs.allowed: raise ValueError("QUOTA_EXCEEDED_LIVENESS")
                r = LivenessService().run(image_live_base64=inp["image_live_base64"], hints=inp.get("hints"))
                res["liveness"] = {"is_live": r.is_live, "spoof_type": r.spoof_type, "confidence": r.confidence, "processing_ms": r.processing_ms}
                record_usage(tenant_id=tenant.id, module="liveness", billed=True)
                if not r.is_live:  # bloquant
                    break

            if step == "ocr":
                qs = check_and_increment_quota(tenant, "ocr", 1)
                if not qs.allowed: raise ValueError("QUOTA_EXCEEDED_OCR")
                ocr = OcrService().run(
                    image_front_base64=inp["image_doc_front_base64"],
                    image_back_base64=inp.get("image_doc_back_base64"),
                    document_hint=inp.get("document_hint","auto"),
                    country_hint=inp.get("country_hint","auto"),
                )
                res["ocr"] = {
                    "detected": {"type": ocr.detected.type, "country": ocr.detected.country, "confidence": ocr.detected.confidence},
                    "fields": ocr.fields,
                    "images": {"face_crop_base64": ocr.face_crop_base64},
                    "quality": ocr.quality,
                }
                record_usage(tenant_id=tenant.id, module="ocr", billed=True)

            if step == "validate":
                qs = check_and_increment_quota(tenant, "validate", 1)
                if not qs.allowed: raise ValueError("QUOTA_EXCEEDED_VALIDATE")
                det = res.get("ocr", {}).get("detected") or inp.get("detected")
                fld = res.get("ocr", {}).get("fields") or inp.get("fields")
                if not det or not fld: raise ValueError("VALIDATE_MISSING_OCR")
                v = validate_document(detected=det, fields=fld)
                res["validate"] = {"document_valid": v.document_valid, "checks": v.checks, "confidence": v.confidence}
                record_usage(tenant_id=tenant.id, module="validate", billed=True)
                if not v.document_valid:  # bloquant
                    break

            if step == "face_match":
                qs = check_and_increment_quota(tenant, "face_match", 1)
                if not qs.allowed: raise ValueError("QUOTA_EXCEEDED_FACE")
                live_b64 = inp["image_live_base64"]
                ref_b64 = res.get("ocr",{}).get("images",{}).get("face_crop_base64") or inp.get("image_ref_base64")
                fm = face_match(image_live_base64=live_b64, image_ref_base64=ref_b64, threshold=min_similarity)
                res["face_match"] = {"match": fm.match, "similarity": fm.similarity, "threshold": min_similarity}
                record_usage(tenant_id=tenant.id, module="face_match", billed=True)
                if not fm.match:
                    break

            if step == "score":
                score = 0.0
                if "liveness" in res and res["liveness"].get("is_live"): score += 30
                if "face_match" in res and res["face_match"].get("similarity",0) >= min_similarity: score += 40
                if "validate" in res and res["validate"].get("document_valid"): score += 25
                # KYA basique (non couvert ici) : +5 potentiels
                decision = "accepted" if score >= min_score_accept else ("review" if score >= 60 else "rejected")
                res["score"] = {"value": round(score,2), "decision": decision, "reasons": []}

        job.status = Job.STATUS_S if res.get("score",{}).get("value",0) >= 60 else Job.STATUS_S  # succeeded même si review/rejected (le job a tourné)
        job.result_json = res
        job.finished_at = timezone.now()
        job.save(update_fields=["status","result_json","finished_at"])
        _emit(tenant, "job.succeeded", {"job_id": job.id, "result": res})
        return

    except Exception as e:
        job.status = Job.STATUS_F
        job.error_json = {"message": str(e)}
        job.finished_at = timezone.now()
        job.save(update_fields=["status","error_json","finished_at"])
        _emit(tenant, "job.failed", {"job_id": job.id, "error": job.error_json})
        return

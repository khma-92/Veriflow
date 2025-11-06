from django.test import TestCase, Client
import base64, time, hmac, hashlib, json
from tenants.models import Plan, Tenant
from apikeys.models import ApiKey
from jobs.models import Job

class WorkflowApiTest(TestCase):
    def setUp(self):
        plan = Plan.objects.create(name="Pro", slug="pro", per_minute=120, per_day=100000,
                                   quotas={"liveness_monthly":5000,"ocr_monthly":5000,"validate_monthly":5000,"face_match_monthly":5000},
                                   unit_prices={"liveness":0.02,"ocr":0.08,"validate":0.01,"face_match":0.05})
        self.tenant = Tenant.objects.create(name="ACME", plan=plan, country_code="CI")
        self.key = ApiKey.objects.create(tenant=self.tenant, key_id="kid_wf", key_secret_enc="plain:secret_wf")
        self.client = Client()

    def _headers(self, method, path, body: bytes):
        ts = str(int(time.time()*1000))
        body_sha = hashlib.sha256(body).hexdigest()
        to_sign = f"{ts}\n{method}\n{path}\n{body_sha}".encode()
        sign = hmac.new(b"secret_wf", to_sign, hashlib.sha256).hexdigest()
        return {"HTTP_X_API_KEY": self.key.key_id, "HTTP_X_API_TIMESTAMP": ts, "HTTP_X_API_SIGN": sign, "CONTENT_TYPE":"application/json"}

    def test_queue_job(self):
        body = {
            "steps": ["liveness","ocr","validate","face_match","score"],
            "inputs": {
                "image_live_base64": base64.b64encode(b"\x89PNG live").decode(),
                "image_doc_front_base64": base64.b64encode(b"\x89PNG doc").decode(),
                "face_threshold": 0.75
            },
            "rules": {"min_score_accept": 80, "min_similarity": 0.75}
        }
        path = "/api/v1/kyc/verify"
        payload = json.dumps(body, separators=(",",":")).encode()
        resp = self.client.post(path, data=payload, **self._headers("POST", path, payload))
        self.assertEqual(resp.status_code, 202, resp.content)
        job_id = resp.json()["job_id"]
        self.assertTrue(Job.objects.filter(id=job_id).exists())

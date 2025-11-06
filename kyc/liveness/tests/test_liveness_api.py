from django.test import TestCase, Client
from django.urls import reverse
import base64, time, hmac, hashlib
from tenants.models import Plan, Tenant
from apikeys.models import ApiKey

class LivenessApiTest(TestCase):
    def setUp(self):
        self.plan = Plan.objects.create(name="Pro", slug="pro", per_minute=120, per_day=100000,
                                        quotas={"liveness_monthly": 5000}, unit_prices={"liveness": 0.02})
        self.tenant = Tenant.objects.create(name="ACME", plan=self.plan, country_code="CI")
        # Clé HMAC en clair DEV
        self.key = ApiKey.objects.create(tenant=self.tenant, key_id="kid_123", key_secret_hash="plain:secret123")
        self.client = Client()

    def _headers(self, method, path, body: bytes):
        ts = str(int(time.time()*1000))
        body_sha = hashlib.sha256(body).hexdigest()
        to_sign = f"{ts}\n{method}\n{path}\n{body_sha}".encode()
        sign = hmac.new(b"secret123", to_sign, hashlib.sha256).hexdigest()
        return {
            "HTTP_X_API_KEY": self.key.key_id,
            "HTTP_X_API_TIMESTAMP": ts,
            "HTTP_X_API_SIGN": sign,
            "CONTENT_TYPE": "application/json",
        }

    def test_ok(self):
        img_b64 = base64.b64encode(b"\x89PNGfake").decode()
        path = "/api/v1/liveness/analyze"
        body = (f'{{"image_live_base64":"{img_b64}","hints":{{"blink":true}}}}').encode()
        resp = self.client.post(path, data=body, **self._headers("POST", path, body))
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertIn("is_live", data)
        self.assertIn("confidence", data)

    def test_invalid_base64(self):
        path = "/api/v1/liveness/analyze"
        body = b'{"image_live_base64":"@@@invalid@@@"}'
        resp = self.client.post(path, data=body, **self._headers("POST", path, body))
        self.assertEqual(resp.status_code, 400)

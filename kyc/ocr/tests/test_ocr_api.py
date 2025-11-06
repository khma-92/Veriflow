from django.test import TestCase, Client
import base64, time, hmac, hashlib
from tenants.models import Plan, Tenant
from apikeys.models import ApiKey

class OcrApiTest(TestCase):
    def setUp(self):
        self.plan = Plan.objects.create(name="Pro", slug="pro", per_minute=120, per_day=100000,
                                        quotas={"ocr_monthly": 5000}, unit_prices={"ocr": 0.08})
        self.tenant = Tenant.objects.create(name="ACME", plan=self.plan, country_code="CI")
        self.key = ApiKey.objects.create(tenant=self.tenant, key_id="kid_ocr", key_secret_enc="plain:secret_ocr")
        self.client = Client()

    def _headers(self, method, path, body: bytes):
        ts = str(int(time.time()*1000))
        body_sha = hashlib.sha256(body).hexdigest()
        to_sign = f"{ts}\n{method}\n{path}\n{body_sha}".encode()
        sign = hmac.new(b"secret_ocr", to_sign, hashlib.sha256).hexdigest()
        return {
            "HTTP_X_API_KEY": self.key.key_id,
            "HTTP_X_API_TIMESTAMP": ts,
            "HTTP_X_API_SIGN": sign,
            "CONTENT_TYPE": "application/json",
        }

    def test_ok(self):
        front_b64 = base64.b64encode(b"\x89PNG ... front image bytes ...").decode()
        path = "/api/v1/document/ocr"
        body = (f'{{"image_front_base64":"{front_b64}","document_hint":"auto","country_hint":"auto"}}').encode()
        resp = self.client.post(path, data=body, **self._headers("POST", path, body))
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertIn("detected", data)
        self.assertIn("fields", data)
        self.assertIn("images", data)

    def test_invalid_front(self):
        path = "/api/v1/document/ocr"
        body = b'{"image_front_base64":"@@@invalid@@@"}'
        resp = self.client.post(path, data=body, **self._headers("POST", path, body))
        self.assertEqual(resp.status_code, 400)

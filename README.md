![Banner](veriFlow.png)

# 1) Objectives & Scope

* **Functional goal:** Verify a person’s identity remotely via:

  1. **Live photo (liveness + anti-spoof)**
  2. **Identity document** (detection & OCR for documents worldwide)
  3. **Face matching** (live photo ↔ document photo)
  4. **Structural validation** of document fields (MRZ, country codes, dates, formats, checksums…)
  5. **Overall validity score** + structured **data extraction**
* **Technical scope:** Secure REST API, **multi-tenant**, **multi-region**, with **observability**, **usage-based billing**, **quotas & rate limits**, **webhooks**, **audit logs**, and **GDPR-like compliance**.
* **Usage modes:**

  * **Standalone API calls** (each module can run independently)
  * **Full workflow** (configurable processing pipeline)

---

# 2) Roles & Actors

* **Super-admin (platform operator):** manages clients, plans, pricing, SLAs, API keys, quotas, logs.
* **Client (tenant):** holds API keys, configures webhooks, views dashboards, downloads logs.
* **System:** asynchronous services (Celery) for heavy jobs & webhook dispatching.

---

# 3) Functional Modules (billable per call)

1. **Liveness & Anti-spoof**

   * Detects real-time capture (blink/pose/gaze) & **spoof attempts** (screen, print, mask, rephoto).
   * Output: `is_live` (bool), `spoof_type` (enum), `confidence` (0–1), `hints`.

2. **Document Detection & OCR**

   * **Auto-detects** type (passport, ID card, license, residence permit) + country.
   * **Extracts fields** (NAME, GIVEN NAMES, DOB, document number, sex, nationality, dates, MRZ, etc.).
   * **Normalizes** (ISO date, ISO-3166 country, doc type).

3. **Document Validation**

   * Formal checks (MRZ checksum, field lengths, date consistency, coherence).
   * Detects **missing areas**, **alterations**, **bad cropping**.
   * Output: `document_valid` (bool), `checks[]`, `confidence`.

4. **Face Match**

   * Compares **live photo** ↔ **document face** (or stored user photo).
   * Output: `match` (bool), `similarity` (0–1), customizable thresholds.

5. **Full e-KYC Workflow**

   * Orchestration: `liveness → ocr → validate → face_match → scoring`.
   * Customizable: order, thresholds, mandatory fields, rules.

6. **KYA (Basic Profile) – Optional**

   * Lightweight checks (email MX, E.164 phone format, country/IP, name coherence).
   * No AML in this version (can be added as paid module).

---

# 4) Scoring Model

* **Overall Score (0–100)**, weighted as:

  * Liveness (30) + Face-match (40) + Doc validation (25) + KYA (5)

* **Default thresholds (tenant-customizable):**

  * **Accepted** ≥ 80
  * **Manual review** 60–79
  * **Rejected** < 60

* **Explanations:** Detailed reasons per factor (e.g., “MRZ checksum fail”, “similarity 0.62 < 0.75 threshold”).

---

# 5) Technical Architecture

* **Backend:** Django 4.x, DRF 3.x, Python 3.11+
* **Workers:** Celery + Redis/RabbitMQ
* **Storage:** PostgreSQL 14+ (logical multi-tenancy), S3-compatible media
* **AI / Vision integrations:** provider-agnostic connectors (OpenCV, InsightFace, TensorRT, Tesseract, Cloud OCR…)
* **Observability:** Prometheus metrics, OpenTelemetry tracing, ELK logs
* **Security:** API-Key + **HMAC signature** (timestamped, anti-replay), TLS 1.2+, encryption at rest

---

# 6) Security, Compliance & Privacy

* **PII** encrypted at rest (AES-256) and in transit (TLS).
* **Tenant-level data isolation** via scoped API keys.
* **Media retention** configurable (e.g., 30 days) then secure deletion.
* **Right to erasure**, **privacy by design**, **immutable audit log** (WORM).
* **Rate limits** global and per endpoint (e.g., 60 req/min/key).
* **Secret rotation** and **API key rollover** supported.
* **Upload policy:** MIME-type + size checks, antivirus (ClamAV), EXIF stripping.

---

# 7) Multi-Tenancy, Accounts & Billing

* **Tenant:** name, country, support email, **plan**, **monthly quotas**.
* **API Keys:** `api_key_id` (public) + `api_key_secret` (never re-shown) + **HMAC**.
* **Quota:** per module (e.g., 5k liveness / month).
* **Billing:** usage-based (metered events table).
* **Plans:** Free (sandbox), Pro, Enterprise (SLA, support, dedicated region).
* **Soft limit handling:** HTTP 429 + webhook for thresholds (80%, 100%).

---

# 8) API Endpoints (DRF)

Base URL (prod): `https://api.example.com/v1/`
Auth headers: `X-API-KEY`, `X-API-TIMESTAMP`, `X-API-SIGN` (HMAC SHA256 of body + timestamp)

## 8.1 Liveness / Anti-Spoof

`POST /liveness/analyze`

```json
{
  "image_live_base64": "<...>",
  "hints": {"pose": true, "blink": true}
}
```

**200 Response**

```json
{
  "is_live": true,
  "spoof_type": "none|screen|paper|mask|unknown",
  "confidence": 0.93,
  "processing_ms": 428,
  "usage": {"module": "liveness", "billed": true}
}
```

## 8.2 Document OCR (Auto-Detection)

`POST /document/ocr`

```json
{
  "image_front_base64": "<...>",
  "image_back_base64": "<optional>",
  "document_hint": "auto|passport|id_card|driver_license",
  "country_hint": "auto|CIV|FRA|USA"
}
```

**200 Response**

```json
{
  "detected": {"type": "passport", "country": "CIV", "confidence": 0.88},
  "fields": {...},
  "images": {"face_crop_base64": "<...>"},
  "quality": {"sharpness": 0.81, "glare": 0.07}
}
```

## 8.3 Document Validation

`POST /document/validate`

**200 Response**

```json
{
  "document_valid": true,
  "checks": [{"name": "mrz_checksum", "status": "pass"}],
  "confidence": 0.9
}
```

## 8.4 Face Match

`POST /face/match`

**200 Response**

```json
{"match": true, "similarity": 0.84, "threshold": 0.75}
```

## 8.5 Full Workflow

`POST /kyc/verify`

Async execution with webhook callback.
Returns job ID and `queued` status.

---

# 9) Database Schema (Simplified)

* **Tenant**, **ApiKey**, **Job**, **UsageEvent**, **RateLimit**, **MediaStore**, **AuditLog**

Images stored in S3; database holds only metadata & encrypted URLs.

---

# 10) Processing Flow

1. Client → `/kyc/verify` → creates **Job** (queued)
2. Celery executes steps → stores result → sends **webhook**.

---

# 11) Performance & Limits

* **SLA:** 99.5% (Pro), 99.9% (Enterprise)
* **Target latencies (p95)**: liveness <1200ms, OCR <1800ms, pipeline <3500ms
* **Max upload:** 10MB / image (JPG/PNG/WebP)
* **Rate-limit:** 60 rpm / 50k per day (default)

---

# 12) Logging & Observability

Request logs, app logs, audit logs, metrics (latency, error rates, quotas), tracing (OpenTelemetry).

---

# 13) Quality, Tests & Sandbox

Environments: `dev`, `sandbox`, `prod`
OpenAPI 3.1 (Swagger), synthetic test sets, load & security tests (OWASP ASVS).

---

# 14) Error Handling

Consistent JSON error format with `error.code`, `message`, `details`, `trace_id`.

---

# 15) Enums

* `spoof_type`: `none|screen|paper|mask|deepfake|unknown`
* `document_type`: `passport|id_card|driver_license|residence_permit|other`
* `decision`: `accepted|review|rejected`
* `module`: `liveness|ocr|validate|face_match|workflow`

---

# 16) Pricing & Metering (Example)

| Module     | Price (USD)                     |
| ---------- | ------------------------------- |
| Liveness   | 0.01–0.03                       |
| OCR        | 0.05–0.12                       |
| Validation | 0.01                            |
| Face-match | 0.02–0.05                       |
| Workflow   | sum of modules (discount tiers) |

---

# 17) API Security (HMAC)

Headers:

* `X-API-KEY`
* `X-API-TIMESTAMP`
* `X-API-SIGN = hex(hmac_sha256(secret, timestamp + '\n' + method + '\n' + path + '\n' + body_sha256))`

Clock skew tolerance ±5 min, replay protection enabled.

---

# 18) Operator Back-Office

Manage tenants, keys, plans, quotas, monitoring, logs, and billing.

---

# 19) Deployment & SRE

Kubernetes (autoscaling), S3 (WORM), PostgreSQL HA, CI/CD (blue-green deploy), encrypted backups.

---

# 20) Roadmap

AML, biometric enrollment, advanced fraud (deepfake), SDKs (mobile), no-code rule builder.

---

# 21) Non-Functional Requirements

Availability ≥ SLA
Scalable horizontally (GPU nodes optional)
End-to-end traceability (audit, telemetry)
OpenAPI documentation + Postman examples.

---

# 22) Deliverables

1. OpenAPI spec + Postman collection (HMAC-ready)
2. Integration guide (webhooks, idempotency, best practices)
3. Test datasets (images, expected outputs)
4. Dashboards (usage, errors, invoices)
5. Back-office tools (tenants, quotas, logs)
6. SLA & support contract.

---

# 23) Acceptance Criteria

Fully operational workflow
Independent module endpoints
Customizable scoring
Accurate billing & quotas
Verified HMAC security
Operational observability
Data retention compliance.

---
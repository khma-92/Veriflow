<p align="center">
  <img src="./VeriFlow.png" alt="VeriFlow Logo" width="400"/>
</p>

# 1) Objectifs & portée

* **Objectif fonctionnel :** vérifier l’identité d’un individu à distance via:

  1. **Photo live (liveness + anti-spoof)**
  2. **Pièce d’identité** (détection & OCR pour documents du monde entier)
  3. **Correspondance visage** (photo live ↔ photo sur la pièce)
  4. **Validation structurelle** des champs document (MRZ, codes pays, dates, format, checksum…)
  5. **Score global de validité** + restitution **structurée** des données extraites
* **Portée technique :** API REST sécurisée, **multi-tenant**, **multi-région**, **observabilité**, **facturation par module**, **quotas & rate-limits**, **webhooks**, **audit** et **conformité RGPD-like**.
* **Modes d’usage :**

  * Appels **unitaires** (chaque module indépendant)
  * **Workflow complet** (pipeline configurable)

---

# 2) Rôles & acteurs

* **Super-admin (opérateur plateforme)** : gère clients, plans, tarifs, SLA, clés, quotas, logs.
* **Client (tenant)** : dispose de clés API, paramètre ses webhooks, consulte tableaux de bord, télécharge logs.
* **Système** : services asynchrones (Celery) pour traitements lourds & webhooks.

---

# 3) Modules fonctionnels (facturables à l’appel)

1. **Liveness & anti-spoof**

   * Détection de “live capture” (blink/pose/gaze) & **anti-spoof** (écran, papier, photo re-photographiée).
   * Sorties : `is_live` (bool), `spoof_type` (enum), `confidence` (0–1), `hints`.
2. **Détection & OCR de document**

   * **Auto-détection** du type (passeport, CNI, permis, titre de séjour…) + pays.
   * **Extraction champs** (NOM, PRÉNOMS, DOB, numéro doc, sexe, nationalité, dates, MRZ, etc.).
   * **Normalisation** (format date ISO, pays ISO-3166, type doc).
3. **Validation document**

   * Contrôles formels (MRZ checksum, longueurs, plages de dates, cohérences).
   * Détection **zones manquantes** / **altération** / **recadrage** insuffisant.
   * Sorties : `document_valid` (bool), `checks[]` (liste détaillée), `confidence`.
4. **Face-Match (comparaison)**

   * Similarité **photo live** ↔ **photo du document** (ou photo “selfie” fournie).
   * Sorties : `match` (bool), `similarity` (0–1), seuils personnalisables par client.
5. **Workflow e-KYC complet**

   * Orchestration : `liveness → ocr → validation → face-match → scoring`.
   * Personnalisable : ordre, seuils, règles métiers, champs obligatoires.
6. **KYA (profil de base) – optionnel**

   * Vérifs légères (email MX, téléphone format E.164, pays/IP, cohérence nom/prénom caractères…).
   * Pas d’AML dans ce périmètre (peut être ajouté plus tard comme module payant).

---

# 4) Modèle de scoring

* **Score global (0–100)**, pondéré :

  * Liveness (30) + Face-match (40) + Validation doc (25) + KYA basique (5)
* **Seuils par défaut (personnalisables par tenant)** :

  * **Accepté** ≥ 80
  * **Revue manuelle** 60–79
  * **Rejeté** < 60
* **Justifications** : explication par facteur (ex. “MRZ checksum fail”, “similarity 0.62 < 0.75 threshold”).

---

# 5) Architecture technique

* **Backend** : Django 4.x, DRF 3.x, Python 3.11+
* **Workers** : Celery + Redis/RabbitMQ
* **Stockage** : PostgreSQL 14+ (multi-tenant logique), S3-compatible pour médias
* **Intégrations IA / Vision** : connecteurs “provider-agnostic” (pluggable : OpenCV/InsightFace/TensorRT, Tesseract/Cloud OCR, etc.)
* **Observabilité** : Prometheus metrics, OpenTelemetry traces, ELK logs
* **Sécurité** : API-Key + **HMAC signature** (horodatage, anti-replay), TLS 1.2+, chiffrement at-rest

---

# 6) Sécurité, conformité & confidentialité

* **PII** chiffrées at-rest (AES-256) & en transit (TLS).
* **Séparation logique par tenant**, scoping par clés API.
* **Rétention média** configurable (ex. 30 jours) puis purge sécurisée.
* **Droit à l’effacement**, **privacy by design**, **journal d’audit** immuable (WORM).
* **Rate-limit** global & par endpoint (p. ex. 60 req/min/clé).
* **Secret scanning** & rotation de clés (rollover).
* **Politique d’uploads** : type MIME & taille, antivirus (ClamAV), supprimer EXIF.

---

# 7) Multi-tenant, comptes & facturation

* **Tenant** : nom, pays, email support, **plan tarifaire**, quotas mensuels.
* **Clés API** : `api_key_id` public + `api_key_secret` (non réaffiché) + **HMAC**.
* **Quota** : par module (ex. 5k liveness / mois).
* **Facturation** : **metering** à l’appel avec table des “usage events”.
* **Plans** : Free (sandbox), Pro, Enterprise (SLA, support, région dédiée).
* **Refus soft** si quota dépassé (HTTP 429) + webhook de seuil (80%, 100%).

---

# 8) Endpoints (DRF) – schémas d’API

Base URL (prod) : `https://api.example.com/v1/`
Auth : Headers `X-API-KEY`, `X-API-TIMESTAMP`, `X-API-SIGN` (HMAC SHA256 du body + timestamp)

## 8.1 Liveness / anti-spoof

`POST /liveness/analyze`

```json
{
  "image_live_base64": "<...>",
  "hints": {"pose": true, "blink": true}
}
```

**200**

```json
{
  "is_live": true,
  "spoof_type": "none|screen|paper|mask|unknown",
  "confidence": 0.93,
  "processing_ms": 428,
  "usage": {"module": "liveness", "billed": true}
}
```

## 8.2 OCR document (auto-détection)

`POST /document/ocr`

```json
{
  "image_front_base64": "<...>",
  "image_back_base64": "<... optional ...>",
  "document_hint": "auto|passport|id_card|driver_license",
  "country_hint": "auto|CIV|FRA|USA"
}
```

**200**

```json
{
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
  "quality": {"sharpness": 0.81, "glare": 0.07}
}
```

## 8.3 Validation document

`POST /document/validate`

```json
{
  "detected": {"type": "passport", "country": "CIV"},
  "fields": {"mrz": "P<CIV...", "dob": "1999-08-16", "expiry_date": "2029-08-15"}
}
```

**200**

```json
{
  "document_valid": true,
  "checks": [
    {"name": "mrz_checksum", "status": "pass"},
    {"name": "expiry_future", "status": "pass"},
    {"name": "dob_past", "status": "pass"}
  ],
  "confidence": 0.9
}
```

## 8.4 Face-match

`POST /face/match`

```json
{
  "image_live_base64": "<...>",
  "image_ref_base64": "<face_from_document_or_user_ref>",
  "threshold": 0.75
}
```

**200**

```json
{
  "match": true,
  "similarity": 0.84,
  "threshold": 0.75
}
```

## 8.5 Workflow complet (orchestration)

`POST /kyc/verify`

```json
{
  "steps": ["liveness","ocr","validate","face_match","score"],
  "inputs": {
    "image_live_base64": "<...>",
    "image_doc_front_base64": "<...>",
    "image_doc_back_base64": "<optional>",
    "face_threshold": 0.75
  },
  "rules": {
    "min_score_accept": 80,
    "min_similarity": 0.75,
    "require_back_image": false
  },
  "webhook_url": "https://client.example.com/hooks/kyc"
}
```

**202** (asynchrone recommandé)

```json
{"job_id":"job_01HR...","status":"queued"}
```

`GET /jobs/{job_id}`
**200**

```json
{
  "status":"succeeded",
  "result":{
    "liveness": {...},
    "ocr": {...},
    "validate": {...},
    "face_match": {...},
    "score": {"value": 87, "decision": "accepted", "reasons":[]}
  },
  "usage":[
    {"module":"liveness","billed":true},
    {"module":"ocr","billed":true},
    {"module":"validate","billed":true},
    {"module":"face_match","billed":true}
  ]
}
```

## 8.6 Webhooks

* **Événements** : `job.succeeded`, `job.failed`, `quota.threshold`, `quota.exceeded`
* **Signature** : `X-Signature` HMAC (secret webhook du client)

## 8.7 Administration (tenant)

* `POST /tenants` (Super-admin)
* `POST /tenants/{id}/keys` : créer/rotater clés
* `GET /usage?tenant_id=...&from=...&to=...`
* `GET /invoices/{id}` (si facturation gérée)

---

# 9) Modèle de données (PostgreSQL – simplifié)

* **Tenant**(id, name, plan, status, webhook_url, created_at)
* **ApiKey**(id, tenant_id FK, key_id, key_secret_hash, active, created_at, last_used_at)
* **Job**(id, tenant_id, status, started_at, finished_at, result_json, error_json)
* **UsageEvent**(id, tenant_id, module, job_id, request_id, billed, unit_price, created_at)
* **RateLimit**(tenant_id, per_minute, per_day)
* **MediaStore**(id, tenant_id, type, url, sha256, encrypted, expires_at)
* **AuditLog**(id, tenant_id, actor, action, target, ip, ua, created_at)

> **Note** : stockage d’images en S3, table conserve uniquement métadonnées & URL chiffrée.

---

# 10) Flux & séquences (description)

1. **Workflow complet (async)**
   Client → `/kyc/verify` → crée **Job** (status=queued) → **Celery worker** exécute étapes:

   * Liveness → si fail & bloquant ⇒ stop + score bas
   * OCR → normalise champs
   * Validation → applique règles doc/pays
   * Face-match → calcule similarité
   * Scoring → produit décision
     → Sauvegarde résultat → **Webhook** `job.succeeded` → client peut **GET /jobs/{id}`.

2. **Appels unitaires**
   Directement les endpoints par module, **synchrones** (temps < 2–5s).

---

# 11) Performances, SLA & limites

* **SLA Pro** : 99.5% uptime mensuel ; **Enterprise** : 99.9%
* **Temps cible** (p95, en ms) : liveness < 1200, OCR < 1800, face-match < 800, validate < 300; pipeline < 3500 (hors latence réseau).
* **Taille max** upload : 10 Mo / image ; formats : JPG/PNG/WebP.
* **Rate-limit** par clé : par défaut 60 rpm, 50k/jour (paramétrable par plan).
* **Retries** idempotents côté client : `Idempotency-Key` header supporté.

---

# 12) Journalisation & observabilité

* **Request log** (tenant, endpoint, durée, statut, corrélation id).
* **App log** (niveau, stacktrace).
* **Audit log** (actions admin & clés).
* **Metrics** : QPS, latence p50/p95/p99 par endpoint, erreurs (4xx/5xx), ration accept/review/reject, consommation quota & facture estimée.
* **Tracing** : OpenTelemetry (correlation_id propageable via header).

---

# 13) Qualité, tests & sandbox

* **Environnements** : `dev`, `sandbox`, `prod` (clés & quotas distincts).
* **Jeux de tests** : images synthétiques (vrai/faux document, spoof, glare…).
* **Contrats d’API** : OpenAPI 3.1 (Swagger UI).
* **Tests** : unitaires (modules vision, OCR parsers), intégration (pipelines), charge (locust), sécurité (OWASP ASVS).

---

# 14) Gestion des erreurs (convention)

* **4xx** : erreurs client (auth, quota, input invalide).
* **5xx** : erreurs serveur / provider.
* **Payload d’erreur**

```json
{
  "error": {
    "code": "QUOTA_EXCEEDED|INVALID_IMAGE|UNSUPPORTED_DOCUMENT|SPOOF_DETECTED|MRZ_INVALID|FACE_NOT_FOUND",
    "message": "Texte explicatif",
    "details": {...},
    "trace_id": "req_..."
  }
}
```

---

# 15) Sélecteurs & enums (extraits)

* `spoof_type`: `none|screen|paper|mask|deepfake|unknown`
* `document_type`: `passport|id_card|driver_license|residence_permit|other`
* `decision`: `accepted|review|rejected`
* `module`: `liveness|ocr|validate|face_match|workflow`

---

# 16) Tarification & metering (exemple)

* **Liveness**: 0.01–0.03 USD / appel
* **OCR doc**: 0.05–0.12 USD / page
* **Validation**: 0.01 USD / doc
* **Face-match**: 0.02–0.05 USD / appel
* **Workflow complet** = somme modules (avec remise palier)
* **Facturation** mensuelle sur **UsageEvent** agrégé (CSV + PDF).

---

# 17) Sécurité d’API (HMAC)

* Headers requis :

  * `X-API-KEY: <key_id>`
  * `X-API-TIMESTAMP: <epoch_ms>`
  * `X-API-SIGN: hex(hmac_sha256(secret, timestamp + '\n' + method + '\n' + path + '\n' + body_sha256))`
* **Tolérance horloge** : ±5 min ; sinon 401.
* **Anti-replay** : refus si timestamp trop ancien ou déjà vu (cache nonce).

---

# 18) Back-office opérateur

* **Tenants & clés** (CRUD, rotation, suspension).
* **Plans, quotas, tarifs** (catalogue, assignation).
* **Monitoring** (tableaux, alertes quotas, erreurs).
* **Export** (usage, logs, jobs, factures).
* **Outils de support** (rejouer job, scrub PII, purge).

---

# 19) Déploiement & SRE

* **Infra** : Kubernetes (autoscaling HPA), Ingress TLS, secrets (Vault).
* **Stockage** : S3 (ObjectLock pour WORM), Postgres HA.
* **CI/CD** : lint, tests, scan deps, build images, déploiement blue/green.
* **Backup & DR** : snapshots DB chiffrés, restauration testée.

---

# 20) Roadmap (évolutions)

* **AML / Sanctions / PEP** (module payant).
* **Pre-enrollement biométrique** (template visage réutilisable).
* **Fraude avancée** (texture analysis, deepfake detector).
* **SDK mobiles** (iOS/Android) pour capture guidée.
* **Règles no-code** par tenant (seuils, champs requis, scoring custom).

---

# 21) Exigences non-fonctionnelles (résumé)

* **Disponibilité** ≥ SLA plan
* **Scalabilité** horizontale (GPU nodes optionnels)
* **Latence** p95 < 3.5s workflow
* **Sécu** (OWASP, chiffrement, audits)
* **Traçabilité** complète (audit & traces)
* **Docs** (OpenAPI + guides + exemples Postman/Insomnia)

---

# 22) Livrables

1. **Spéc OpenAPI** & **Collection Postman** (auth HMAC incluse)
2. **Guide d’intégration** (webhooks, idempotency, meilleures pratiques capture)
3. **Jeux d’essai** (images & réponses attendues)
4. **Tableau de bord** (consommation, erreurs, jobs, factures)
5. **Back-office** (tenants, clés, quotas, logs)
6. **Contrat SLA & Support** (heures, canaux, MTTR)

---

# 23) Critères d’acceptation

* Workflow complet opérationnel (happy path + erreurs)
* Appels unitaires utilisables **indépendamment**
* Scoring & décisions paramétrables par tenant
* Quotas & facturation exacts au centime
* Sécurité HMAC testée (replay/clock skew)
* Observabilité (dashboards p95, erreurs, consommation)
* Conformité rétention/suppression PII

---

# 24) Annexes – Exemples d’implémentation DRF (squelette)

* **Permissions** : `ApiKeyHmacAuthentication`, `TenantScopedPermission`
* **Views** : `LivenessView`, `DocumentOcrView`, `DocumentValidateView`, `FaceMatchView`, `KycWorkflowView`
* **Serializers** : `LivenessInput`, `OcrInput`, `ValidateInput`, `FaceMatchInput`, `WorkflowInput`
* **Tasks** : `run_kyc_workflow(job_id)`
* **Services** : `LivenessService`, `OcrService`, `ValidationService`, `FaceService`, `ScoringService`
* **Billing** : `UsageRecorder.record(tenant, module, job_id, billed=True)`

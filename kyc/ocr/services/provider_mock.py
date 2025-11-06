import base64, hashlib, time
from .provider import BaseOcrProvider, OcrResult, OcrDetected

class MockOcrProvider(BaseOcrProvider):
    """
    Provider fake/maquette déterministe:
    - Détecte type/pays via quelques heuristiques et hints.
    - "Extrait" des champs plausibles à partir d'un hash.
    - Retourne un face_crop_base64 bidon (premiers octets de front encodés).
    À remplacer par le connecteur réel (Tesseract, Google Vision, provider externe).
    """
    def analyze(self, *, front_bytes: bytes, back_bytes=None, document_hint="auto", country_hint="auto") -> OcrResult:
        t0 = time.perf_counter()
        h = hashlib.sha256(front_bytes[:4096]).hexdigest()

        # Détection type
        doc_type = "passport"
        if document_hint != "auto":
            doc_type = document_hint
        else:
            doc_type = "id_card" if h[0] in "0123" else "driver_license" if h[0] in "456" else "passport"

        # Détection pays (alpha-3)
        cc = "CIV"
        if country_hint != "auto":
            cc = {"CIV":"CIV","FRA":"FRA","USA":"USA"}.get(country_hint, "CIV")
        else:
            cc = "FRA" if h[1] in "abcdef" else "USA" if h[1] in "0123" else "CIV"

        confidence = 0.8

        # Champs OCR "extraits" (maquette)
        fields = {
            "surname": "KOFFI" if cc=="CIV" else ("DUPONT" if cc=="FRA" else "DOE"),
            "given_names": "JEAN MARIE" if cc=="CIV" else ("ALICE MARIE" if cc=="FRA" else "JOHN"),
            "dob": "1999-08-16",
            "document_number": h[2:11].upper(),
            "sex": "M",
            "nationality": cc,
            "expiry_date": "2029-08-15",
            "mrz": f"P<{cc}KOFFI<<JEAN<MARIE<<<<<<<<<<<<<<<<<<<{h[:24].upper()}",
        }

        # Qualité image "mock"
        sharpness = (int(h[2:4],16) % 100) / 100.0
        glare = (int(h[4:6],16) % 15) / 100.0
        quality = {"sharpness": sharpness, "glare": glare}

        # Face crop: on encode une tranche des octets pour simuler
        face_crop_b64 = base64.b64encode(front_bytes[:120]).decode()

        dt_ms = int((time.perf_counter() - t0) * 1000)
        return OcrResult(
            detected=OcrDetected(type=doc_type, country=cc, confidence=confidence),
            fields=fields,
            face_crop_base64=face_crop_b64,
            quality=quality
        )

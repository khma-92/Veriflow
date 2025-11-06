from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class OcrDetected:
    type: str         # "passport" | "id_card" | "driver_license"
    country: str      # ISO-3166 alpha-3 (ex: "CIV", "FRA", "USA")
    confidence: float # 0..1

@dataclass
class OcrResult:
    detected: OcrDetected
    fields: Dict[str, str]      # e.g., {"surname":"KOFFI", "given_names":"JEAN MARIE", "dob":"1999-08-16", ...}
    face_crop_base64: Optional[str]
    quality: Dict[str, float]   # {"sharpness":0.81,"glare":0.07}

class BaseOcrProvider:
    def analyze(self, *, front_bytes: bytes, back_bytes: Optional[bytes], document_hint: str, country_hint: str) -> OcrResult:
        raise NotImplementedError

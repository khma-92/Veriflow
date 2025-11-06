import base64, hashlib
from dataclasses import dataclass

@dataclass
class FaceMatchResult:
    match: bool
    similarity: float

def _sim(a: bytes, b: bytes) -> float:
    # Mock: similarité basée sur xor des premiers octets
    if not a or not b: return 0.0
    L = min(len(a), len(b), 1024)
    score = sum(1 for i in range(L) if a[i]==b[i]) / float(L)
    return float(score)

def face_match(*, image_live_base64: str, image_ref_base64: str, threshold: float) -> FaceMatchResult:
    try:
        a = base64.b64decode(image_live_base64, validate=True)
        b = base64.b64decode(image_ref_base64, validate=True)
    except Exception:
        raise ValueError("INVALID_IMAGE_BASE64")
    if len(a) > 10*1024*1024 or len(b) > 10*1024*1024:
        raise ValueError("INVALID_IMAGE_SIZE")

    sim = _sim(a,b)
    return FaceMatchResult(match=bool(sim >= threshold), similarity=sim)

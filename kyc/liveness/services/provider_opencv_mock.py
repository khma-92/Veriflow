import time, base64
from .provider import BaseLivenessProvider, LivenessResult

class OpenCvMockLivenessProvider(BaseLivenessProvider):
    """
    Implémentation de référence simple (mock) :
    - calcule un hash sur les bytes pour produire un score stable
    - pas de vraie détection, à remplacer par ton moteur (blink/pose/gaze, texture, moiré, etc.)
    """
    def analyze(self, *, image_bytes: bytes, hints=None) -> LivenessResult:
        t0 = time.perf_counter()
        # Faux score reproductible
        s = sum(image_bytes[:2048]) % 100  # pseudo "signal"
        confidence = 0.5 + (s / 200.0)  # [0.5, 1.0)
        confidence = float(min(max(confidence, 0.0), 1.0))

        # Heuristique spoof bidon: si l'image commence par bytes d'une page web/écran (PNG signature), on triche un peu
        spoof = "none"
        if image_bytes.startswith(b"\x89PNG"):
            spoof = "screen" if confidence < 0.8 else "none"

        is_live = spoof == "none" and confidence >= 0.7
        dt_ms = int((time.perf_counter() - t0) * 1000)
        return LivenessResult(is_live=is_live, spoof_type=spoof, confidence=confidence, processing_ms=dt_ms)

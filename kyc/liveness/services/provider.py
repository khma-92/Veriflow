"""
Contrat provider-agnostic pour liveness/anti-spoof.
On pourras brancher un vrai provider (SDK/Cloud). Ici une implémentation mock OpenCV-friendly.
"""
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class LivenessResult:
    is_live: bool
    spoof_type: str  # 'none' | 'screen' | 'paper' | 'mask' | 'deepfake' | 'unknown'
    confidence: float
    processing_ms: int

class BaseLivenessProvider:
    def analyze(self, *, image_bytes: bytes, hints: Optional[Dict[str, bool]] = None) -> LivenessResult:
        raise NotImplementedError

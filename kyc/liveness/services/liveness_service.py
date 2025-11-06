import base64
from typing import Dict, Optional
from .provider import BaseLivenessProvider, LivenessResult
from .provider_opencv_mock import OpenCvMockLivenessProvider

class LivenessService:
    """
    Orchestrateur: validation d'input, décodage base64, appel provider.
    """
    def __init__(self, provider: Optional[BaseLivenessProvider] = None) -> None:
        self.provider = provider or OpenCvMockLivenessProvider()

    def run(self, *, image_live_base64: str, hints: Optional[Dict[str, bool]] = None) -> LivenessResult:
        try:
            image_bytes = base64.b64decode(image_live_base64, validate=True)
        except Exception:
            raise ValueError("INVALID_IMAGE_BASE64")

        if not image_bytes or len(image_bytes) > 10 * 1024 * 1024:  # 10MB
            raise ValueError("INVALID_IMAGE_SIZE")

        return self.provider.analyze(image_bytes=image_bytes, hints=hints or {})

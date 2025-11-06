import base64
from typing import Optional
from .provider import BaseOcrProvider, OcrResult
from .provider_mock import MockOcrProvider

ALLOWED_MAX = 10 * 1024 * 1024  # 10MB

class OcrService:
    def __init__(self, provider: Optional[BaseOcrProvider] = None) -> None:
        self.provider = provider or MockOcrProvider()

    def run(self, *, image_front_base64: str, image_back_base64: Optional[str],
            document_hint: str, country_hint: str) -> OcrResult:
        try:
            front_bytes = base64.b64decode(image_front_base64, validate=True)
        except Exception:
            raise ValueError("INVALID_FRONT_IMAGE_BASE64")
        if not front_bytes or len(front_bytes) > ALLOWED_MAX:
            raise ValueError("INVALID_FRONT_IMAGE_SIZE")

        back_bytes = None
        if image_back_base64:
            try:
                back_bytes = base64.b64decode(image_back_base64, validate=True)
            except Exception:
                raise ValueError("INVALID_BACK_IMAGE_BASE64")
            if len(back_bytes) > ALLOWED_MAX:
                raise ValueError("INVALID_BACK_IMAGE_SIZE")

        return self.provider.analyze(
            front_bytes=front_bytes,
            back_bytes=back_bytes,
            document_hint=document_hint,
            country_hint=country_hint,
        )

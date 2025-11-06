from rest_framework import serializers

class OcrOutputSerializer(serializers.Serializer):
    detected = serializers.DictField()  # {"type": "...", "country": "...", "confidence": float}
    fields = serializers.DictField()    # normalisés (ISO, dates ISO, etc.)
    images = serializers.DictField()    # {"face_crop_base64": "<...>"} (si dispo)
    quality = serializers.DictField()   # {"sharpness": float, "glare": float}

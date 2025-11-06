from rest_framework import serializers

DOCUMENT_HINT_CHOICES = ["auto","passport","id_card","driver_license"]
COUNTRY_HINT_CHOICES = ["auto","CIV","FRA","USA"]

class OcrInputSerializer(serializers.Serializer):
    image_front_base64 = serializers.CharField()
    image_back_base64 = serializers.CharField(required=False, allow_blank=True)
    document_hint = serializers.ChoiceField(choices=DOCUMENT_HINT_CHOICES, default="auto")
    country_hint = serializers.ChoiceField(choices=COUNTRY_HINT_CHOICES, default="auto")

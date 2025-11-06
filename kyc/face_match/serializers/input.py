from rest_framework import serializers

class FaceMatchInputSerializer(serializers.Serializer):
    image_live_base64 = serializers.CharField()
    image_ref_base64 = serializers.CharField()
    threshold = serializers.FloatField(default=0.75)

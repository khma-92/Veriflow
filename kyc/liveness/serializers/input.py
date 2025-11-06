from rest_framework import serializers

class LivenessInputSerializer(serializers.Serializer):
    image_live_base64 = serializers.CharField()
    hints = serializers.DictField(child=serializers.BooleanField(), required=False)

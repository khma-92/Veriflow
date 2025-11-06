from rest_framework import serializers

class FaceMatchOutputSerializer(serializers.Serializer):
    match = serializers.BooleanField()
    similarity = serializers.FloatField()
    threshold = serializers.FloatField()

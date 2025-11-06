from rest_framework import serializers

class ValidateOutputSerializer(serializers.Serializer):
    document_valid = serializers.BooleanField()
    checks = serializers.ListField(child=serializers.DictField())
    confidence = serializers.FloatField()

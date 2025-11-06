from rest_framework import serializers

class LivenessOutputSerializer(serializers.Serializer):
    is_live = serializers.BooleanField()
    spoof_type = serializers.ChoiceField(choices=["none","screen","paper","mask","deepfake","unknown"])
    confidence = serializers.FloatField()
    processing_ms = serializers.IntegerField()
    usage = serializers.DictField()

from rest_framework import serializers
from ..models import ApiKey

class ApiKeyCreateSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField()
    name = serializers.CharField(required=False, allow_blank=True, default="")
    allowed_ips = serializers.ListField(
        child=serializers.IPAddressField(), required=False, allow_empty=True
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)

class ApiKeyRotateSerializer(serializers.Serializer):
    key_id = serializers.CharField()

class ApiKeyOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiKey
        fields = ("id", "tenant", "key_id", "active", "allowed_ips", "created_at", "last_used_at", "expires_at", "name")
        read_only_fields = fields

class ApiKeyRevealSerializer(serializers.Serializer):
    key_id = serializers.CharField()
    key_secret = serializers.CharField()

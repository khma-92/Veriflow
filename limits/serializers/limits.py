from rest_framework import serializers

from limits.models import TenantLimitOverride


class TenantLimitOverrideOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantLimitOverride
        fields = ("tenant", "per_minute", "per_day", "quotas_override", "updated_at")
        read_only_fields = ("updated_at",)

class TenantLimitOverrideUpsertSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantLimitOverride
        fields = ("tenant", "per_minute", "per_day", "quotas_override")

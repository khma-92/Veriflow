from rest_framework import serializers
from ..models import Tenant, Plan


class TenantOutSerializer(serializers.ModelSerializer):
    plan = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = (
            "id", "name", "status", "plan", "country_code", "support_email",
            "webhook_url", "metadata", "created_at", "updated_at", "last_usage_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "last_usage_at")

    def get_plan(self, obj: Tenant):
        p: Plan = obj.plan
        return {
            "id": p.id,
            "slug": p.slug,
            "per_minute": p.per_minute,
            "per_day": p.per_day,
            "quotas": p.quotas,
            "unit_prices": p.unit_prices,
            "sla": p.sla,
            "region": p.region,
        }


class TenantCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = (
            "name", "plan", "country_code", "support_email",
            "webhook_url", "metadata",
        )


class TenantUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = (
            "plan", "country_code", "support_email",
            "webhook_url", "metadata", "status",
        )

from rest_framework import serializers
from ..models import Plan


class PlanOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (
            "id", "name", "slug", "active",
            "per_minute", "per_day",
            "quotas", "unit_prices",
            "sla", "region", "created_at",
        )
        read_only_fields = ("id", "created_at")


class PlanCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (
            "name", "slug", "active",
            "per_minute", "per_day",
            "quotas", "unit_prices",
            "sla", "region",
        )

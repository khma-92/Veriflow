from rest_framework import serializers

from usage.models import UsageEvent


class UsageEventOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageEvent
        fields = ("id", "tenant", "module", "job_id", "request_id", "billed", "unit_price", "amount", "created_at")
        read_only_fields = fields

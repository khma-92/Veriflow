from rest_framework import serializers

from webhooks.models import WebhookConfig, WebhookDelivery


class WebhookConfigOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookConfig
        fields = ("tenant", "url", "events", "active", "timeout_s", "max_retries", "backoff_s", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")

class WebhookConfigUpsertSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookConfig
        fields = ("tenant", "url", "secret", "events", "active", "timeout_s", "max_retries", "backoff_s")

class WebhookDeliveryOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = (
            "id", "tenant", "config", "event", "url", "attempt", "headers",
            "payload", "status_code", "ok", "error", "duration_ms", "created_at"
        )
        read_only_fields = fields

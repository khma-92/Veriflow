import secrets
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from ..models import ApiKey
from ..serializers.apikey import (
    ApiKeyCreateSerializer, ApiKeyRotateSerializer, ApiKeyOutSerializer, ApiKeyRevealSerializer
)

class ApiKeyAdminViewSet(viewsets.ViewSet):
    """
    Super-admin only: création/rotation/suspension des clés API.
    ⚠️ Seuls les admins Django peuvent appeler ces endpoints.
    """
    permission_classes = [IsAdminUser]

    def list(self, request):
        qs = ApiKey.objects.select_related("tenant").order_by("-created_at")
        return Response(ApiKeyOutSerializer(qs, many=True).data)

    @transaction.atomic
    def create(self, request):
        ser = ApiKeyCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        # Génère un couple key_id / key_secret (secret NON stocké en clair)
        key_id = secrets.token_hex(16)
        key_secret = secrets.token_urlsafe(32)

        ak = ApiKey(
            tenant_id=data["tenant_id"],
            key_id=key_id,
            active=True,
            allowed_ips=data.get("allowed_ips"),
            expires_at=data.get("expires_at"),
            name=data.get("name", ""),
        )
        ak.set_secret(key_secret)
        ak.save()

        # On renvoie une seule fois le secret au client
        reveal = ApiKeyRevealSerializer({"key_id": key_id, "key_secret": key_secret})
        return Response(reveal.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="rotate")
    @transaction.atomic
    def rotate(self, request):
        ser = ApiKeyRotateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        key_id = ser.validated_data["key_id"]

        ak = get_object_or_404(ApiKey, key_id=key_id, active=True)
        new_secret = secrets.token_urlsafe(32)
        ak.set_secret(new_secret)
        ak.last_used_at = timezone.now()
        ak.save(update_fields=["key_secret_hash", "last_used_at"])

        reveal = ApiKeyRevealSerializer({"key_id": ak.key_id, "key_secret": new_secret})
        return Response(reveal.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="suspend")
    def suspend(self, request):
        key_id = request.data.get("key_id")
        ak = get_object_or_404(ApiKey, key_id=key_id)
        ak.active = False
        ak.save(update_fields=["active"])
        return Response({"detail": "suspended"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="resume")
    def resume(self, request):
        key_id = request.data.get("key_id")
        ak = get_object_or_404(ApiKey, key_id=key_id)
        ak.active = True
        ak.save(update_fields=["active"])
        return Response({"detail": "resumed"}, status=status.HTTP_200_OK)

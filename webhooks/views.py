from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import viewsets, mixins, status
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import WebhookConfig, WebhookDelivery
from .serializers.webhooks import WebhookConfigOutSerializer, WebhookConfigUpsertSerializer, \
    WebhookDeliveryOutSerializer
from .tasks import deliver_webhook_task

class WebhookConfigAdminViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    """
    Super-admin: gérer la config des webhooks pour chaque tenant.
    """
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return WebhookConfig.objects.select_related("tenant").all().order_by("tenant_id")

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response(WebhookConfigOutSerializer(qs, many=True).data)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(WebhookConfigOutSerializer(obj).data)

    @transaction.atomic
    def create(self, request):
        ser = WebhookConfigUpsertSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cfg = ser.save()
        return Response(WebhookConfigOutSerializer(cfg).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def partial_update(self, request, pk=None):
        cfg = get_object_or_404(WebhookConfig, pk=pk)
        ser = WebhookConfigUpsertSerializer(instance=cfg, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        cfg = ser.save()
        return Response(WebhookConfigOutSerializer(cfg).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="test")
    def test_send(self, request, pk=None):
        """
        Déclenche un webhook de test (event="test.ping").
        Body: {"data": {...}} optionnel
        """
        cfg = get_object_or_404(WebhookConfig, pk=pk)
        data = request.data.get("data", {"msg": "hello from VeriFlow"})
        deliver_webhook_task.delay(cfg.id, "test.ping", data, attempt=1)
        return Response({"detail": "queued"}, status=status.HTTP_202_ACCEPTED)


class WebhookDeliveryAdminViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    """
    Super-admin: consultation des livraisons.
    """
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = WebhookDelivery.objects.select_related("tenant", "config").order_by("-created_at")
        tenant_id = self.request.query_params.get("tenant_id")
        event = self.request.query_params.get("event")
        ok = self.request.query_params.get("ok")
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        if event:
            qs = qs.filter(event=event)
        if ok is not None:
            qs = qs.filter(ok=(ok.lower() == "true"))
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response(WebhookDeliveryOutSerializer(qs, many=True).data)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(WebhookDeliveryOutSerializer(obj).data)

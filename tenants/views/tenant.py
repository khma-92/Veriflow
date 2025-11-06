from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import viewsets, status, mixins
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Tenant, Plan
from ..serializers.tenant import (
    TenantOutSerializer, TenantCreateSerializer, TenantUpdateSerializer
)
from ..serializers.plan import PlanOutSerializer, PlanCreateUpdateSerializer


class TenantAdminViewSet(viewsets.GenericViewSet,
                         mixins.ListModelMixin,
                         mixins.RetrieveModelMixin):
    """
    Super-admin: CRUD Tenants + actions (suspend/resume/webhook).
    """
    permission_classes = [IsAdminUser]
    queryset = Tenant.objects.select_related("plan").all().order_by("-created_at")

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(TenantOutSerializer(obj).data)

    @transaction.atomic
    def create(self, request):
        ser = TenantCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tenant = ser.save()
        return Response(TenantOutSerializer(tenant).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def partial_update(self, request, pk=None):
        tenant = get_object_or_404(Tenant, pk=pk)
        ser = TenantUpdateSerializer(instance=tenant, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(TenantOutSerializer(tenant).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        tenant = get_object_or_404(Tenant, pk=pk)
        tenant.status = Tenant.STATUS_SUSPENDED
        tenant.save(update_fields=["status"])
        return Response({"detail": "tenant suspended"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        tenant = get_object_or_404(Tenant, pk=pk)
        tenant.status = Tenant.STATUS_ACTIVE
        tenant.save(update_fields=["status"])
        return Response({"detail": "tenant resumed"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="set-webhook")
    def set_webhook(self, request, pk=None):
        tenant = get_object_or_404(Tenant, pk=pk)
        url = request.data.get("webhook_url", "").strip()
        tenant.webhook_url = url
        tenant.save(update_fields=["webhook_url"])
        return Response({"detail": "webhook updated"}, status=status.HTTP_200_OK)


class PlanAdminViewSet(viewsets.GenericViewSet,
                       mixins.ListModelMixin,
                       mixins.RetrieveModelMixin):
    """
    Super-admin: gestion des Plans.
    """
    permission_classes = [IsAdminUser]
    queryset = Plan.objects.all().order_by("-created_at")

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response(PlanOutSerializer(qs, many=True).data)

    def retrieve(self, request, pk=None):
        p = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(PlanOutSerializer(p).data)

    @transaction.atomic
    def create(self, request):
        ser = PlanCreateUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        p = ser.save()
        return Response(PlanOutSerializer(p).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def partial_update(self, request, pk=None):
        p = get_object_or_404(Plan, pk=pk)
        ser = PlanCreateUpdateSerializer(instance=p, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(PlanOutSerializer(p).data, status=status.HTTP_200_OK)

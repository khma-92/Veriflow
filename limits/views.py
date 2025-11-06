from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import viewsets, status, mixins
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .models import TenantLimitOverride
from .serializers.limits import TenantLimitOverrideOutSerializer, TenantLimitOverrideUpsertSerializer


class TenantLimitOverrideAdminViewSet(viewsets.GenericViewSet,
                                      mixins.ListModelMixin,
                                      mixins.RetrieveModelMixin):
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return TenantLimitOverride.objects.select_related("tenant").all().order_by("tenant_id")

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response(TenantLimitOverrideOutSerializer(qs, many=True).data)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(TenantLimitOverrideOutSerializer(obj).data)

    @transaction.atomic
    def create(self, request):
        ser = TenantLimitOverrideUpsertSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return Response(TenantLimitOverrideOutSerializer(obj).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def partial_update(self, request, pk=None):
        obj = get_object_or_404(TenantLimitOverride, pk=pk)
        ser = TenantLimitOverrideUpsertSerializer(instance=obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return Response(TenantLimitOverrideOutSerializer(obj).data, status=status.HTTP_200_OK)

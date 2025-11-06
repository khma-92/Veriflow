from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAdminUser
from django.utils.timezone import now
from django.db.models import Sum
from .models import UsageEvent
from .serializers.usage import UsageEventOutSerializer


class UsageEventAdminViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    """
    Super-admin: lecture des events de consommation (filtrable via query params).
    """
    permission_classes = [IsAdminUser]
    serializer_class = UsageEventOutSerializer

    def get_queryset(self):
        qs = UsageEvent.objects.select_related("tenant").order_by("-created_at")
        tenant_id = self.request.query_params.get("tenant_id")
        module = self.request.query_params.get("module")
        date_from = self.request.query_params.get("from")
        date_to = self.request.query_params.get("to")
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        if module:
            qs = qs.filter(module=module)
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lt=date_to)
        return qs

    # Petit résumé agrégé (optionnel)
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        qs = self.get_queryset()
        agg = qs.values("module").annotate(total_calls=Sum("amount"))
        response.data = {"results": response.data, "summary": list(agg)}
        return response

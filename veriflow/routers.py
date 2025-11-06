from rest_framework.routers import DefaultRouter

router = DefaultRouter()

# Admin API keys
from apikeys.views.apikey import ApiKeyAdminViewSet
router.register(r"admin/apikeys", ApiKeyAdminViewSet, basename="admin-apikeys")

# Admin Tenants & Plans
from tenants.views.tenant import TenantAdminViewSet, PlanAdminViewSet
router.register(r"admin/tenants", TenantAdminViewSet, basename="admin-tenants")
router.register(r"admin/plans", PlanAdminViewSet, basename="admin-plans")

# Admin Limits overrides
from limits.views import TenantLimitOverrideAdminViewSet
router.register(r"admin/limits/overrides", TenantLimitOverrideAdminViewSet, basename="admin-limits-overrides")

# Admin Usage events
from usage.views import UsageEventAdminViewSet
router.register(r"admin/usage", UsageEventAdminViewSet, basename="admin-usage")

# Admin Webhooks
from webhooks.views import WebhookConfigAdminViewSet, WebhookDeliveryAdminViewSet
router.register(r"admin/webhooks/configs", WebhookConfigAdminViewSet, basename="admin-webhook-configs")
router.register(r"admin/webhooks/deliveries", WebhookDeliveryAdminViewSet, basename="admin-webhook-deliveries")

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WebhookConfigAdminViewSet, WebhookDeliveryAdminViewSet

router = DefaultRouter()
router.register(r"webhooks/configs", WebhookConfigAdminViewSet, basename="admin-webhook-configs")
router.register(r"webhooks/deliveries", WebhookDeliveryAdminViewSet, basename="admin-webhook-deliveries")

urlpatterns = [path("", include(router.urls))]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.tenant import TenantAdminViewSet, PlanAdminViewSet

router = DefaultRouter()
router.register(r"tenants", TenantAdminViewSet, basename="admin-tenants")
router.register(r"plans", PlanAdminViewSet, basename="admin-plans")

urlpatterns = [path("", include(router.urls))]

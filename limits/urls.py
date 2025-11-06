from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TenantLimitOverrideAdminViewSet

router = DefaultRouter()
router.register(r"limits/overrides", TenantLimitOverrideAdminViewSet, basename="admin-limits-overrides")

urlpatterns = [path("", include(router.urls))]

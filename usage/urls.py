from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UsageEventAdminViewSet

router = DefaultRouter()
router.register(r"usage", UsageEventAdminViewSet, basename="admin-usage")

urlpatterns = [path("", include(router.urls))]

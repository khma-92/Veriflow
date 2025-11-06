from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.apikey import ApiKeyAdminViewSet

router = DefaultRouter()
router.register(r"keys", ApiKeyAdminViewSet, basename="apikeys-admin")

urlpatterns = [path("", include(router.urls))]

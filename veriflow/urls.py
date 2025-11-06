from django.contrib import admin
from django.urls import path, include, re_path
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from .routers import router as api_router
from .settings.base import API_PREFIX, API_VERSION, HEALTH_INFO

def health_view(_request):
    return JsonResponse({"status": "ok", **HEALTH_INFO()})

urlpatterns = [
    path("health/", health_view, name="health"),
    path("admin/", admin.site.urls),

    # OpenAPI
    path(f"{API_PREFIX}/{API_VERSION}/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        f"{API_PREFIX}/{API_VERSION}/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
            permission_classes=[AllowAny],
            authentication_classes=[],
        ),
        name="swagger-ui",
    ),
    path(
        f"{API_PREFIX}/{API_VERSION}/redoc/",
        SpectacularRedocView.as_view(
            url_name="schema",
            permission_classes=[AllowAny],
            authentication_classes=[],
        ),
        name="redoc",
    ),

    path(f"{API_PREFIX}/{API_VERSION}/", include(api_router.urls)),
    path(f"{API_PREFIX}/{API_VERSION}/liveness/", include("kyc.liveness.urls")),
    path(f"{API_PREFIX}/{API_VERSION}/document/", include("kyc.ocr.urls")),
    path(f"{API_PREFIX}/{API_VERSION}/document/", include("kyc.validation.urls")),
    path(f"{API_PREFIX}/{API_VERSION}/face/", include("kyc.face_match.urls")),
    path(f"{API_PREFIX}/{API_VERSION}/kyc/", include("kyc.workflow.urls")),
    path(f"{API_PREFIX}/{API_VERSION}/jobs/", include("jobs.urls")),
]


urlpatterns += [
    re_path(
        r"^$",
        SpectacularSwaggerView.as_view(
            url_name="schema",
            permission_classes=[AllowAny],
            authentication_classes=[],
        ),
    ),
]

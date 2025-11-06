from django.urls import path

from kyc.liveness.views.analyze import LivenessAnalyzeView

urlpatterns = [
    path("analyze", LivenessAnalyzeView.as_view(), name="liveness-analyze"),
]

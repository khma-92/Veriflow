from django.urls import path

from kyc.workflow.views.verify import KycWorkflowView

urlpatterns = [ path("verify", KycWorkflowView.as_view(), name="kyc-verify") ]

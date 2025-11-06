from django.urls import path

from kyc.validation.views.validate import DocumentValidateView

urlpatterns = [ path("validate", DocumentValidateView.as_view(), name="document-validate") ]
